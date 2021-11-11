from subprocess import Popen
import ResultData
import sys
import os
import errno
import texttable
import itertools
import numbers
import datetime
import statistics
import subprocess
import re

LOWER_IS_BETTER = 0
HIGHER_IS_BETTER = 1
value_mapping = {
    'read_io_bytes': HIGHER_IS_BETTER,
    'elapsed': LOWER_IS_BETTER,
    'sys_cpu': LOWER_IS_BETTER,
    'read_lat_ns_min': LOWER_IS_BETTER,
    'read_lat_ns_max': LOWER_IS_BETTER,
    'read_clat_ns_p50': LOWER_IS_BETTER,
    'read_clat_ns_p99': LOWER_IS_BETTER,
    'read_iops': HIGHER_IS_BETTER,
    'read_io_kbytes': HIGHER_IS_BETTER,
    'read_bw_bytes': HIGHER_IS_BETTER,
    'write_lat_ns_min': LOWER_IS_BETTER,
    'write_lat_ns_max': LOWER_IS_BETTER,
    'write_iops': HIGHER_IS_BETTER,
    'write_io_kbytes': HIGHER_IS_BETTER,
    'write_bw_bytes': HIGHER_IS_BETTER,
    'write_clat_ns_p50': LOWER_IS_BETTER,
    'write_clat_ns_p99': LOWER_IS_BETTER,
    'throughput': HIGHER_IS_BETTER,

    # These are all latency values from dbench
    'ntcreatex': LOWER_IS_BETTER,
    'close': LOWER_IS_BETTER,
    'rename': LOWER_IS_BETTER,
    'unlink': LOWER_IS_BETTER,
    'deltree': LOWER_IS_BETTER,
    'mkdir': LOWER_IS_BETTER,
    'qpathinfo': LOWER_IS_BETTER,
    'qfileinfo': LOWER_IS_BETTER,
    'qfsinfo': LOWER_IS_BETTER,
    'sfileinfo': LOWER_IS_BETTER,
    'find': LOWER_IS_BETTER,
    'writex': LOWER_IS_BETTER,
    'readx': LOWER_IS_BETTER,
    'lockx': LOWER_IS_BETTER,
    'unlockx': LOWER_IS_BETTER,
    'flush': LOWER_IS_BETTER,
}

# We only mark the whole test as failed if these keys regress
test_regression_keys = [
    'read_bw_bytes',
    'write_bw_bytes',
    'throughput',
    'elapsed'
]

def get_results(session, name, config, purpose, time):
    return session.query(ResultData.Run).\
                outerjoin(ResultData.FioResult).\
                outerjoin(ResultData.DbenchResult).\
                outerjoin(ResultData.TimeResult).\
                filter(ResultData.Run.time >= time).\
                filter(ResultData.Run.name == name).\
                filter(ResultData.Run.purpose == purpose).\
                filter(ResultData.Run.config == config).\
                order_by(ResultData.Run.id).all()

# Shamelessly copied from stackoverflow
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def run_command(cmd, outputfile=None):
    print("  running cmd '{}'".format(cmd))
    need_close = False
    if not outputfile:
        outputfile = open('/dev/null')
        need_close = True
    p = Popen(cmd.split(' '), stdout=outputfile, stderr=outputfile)
    p.wait()
    if need_close:
        outputfile.close()
    if p.returncode == 0:
        return
    print("Command '{}' failed to run".format(cmd))
    sys.exit(1)

def setup_device(config, section):
    device = os.path.basename(config.get(section, 'device'))
    if config.has_option(section, 'iosched'):
        with open(f'/sys/block/{device}/queue/scheduler', 'w') as f:
            f.write(config.get(section, 'iosched'))

def mkfs(config, section):
    if not config.has_option(section, 'mkfs'):
        return
    device = config.get(section, 'device')
    mkfs_cmd = config.get(section, 'mkfs')
    run_command(f'{mkfs_cmd} {device}')

def mount(config, section):
    if not config.has_option(section, 'mount'):
        return
    device = config.get(section, 'device')
    mnt = config.get('main', 'directory')
    mount_cmd = config.get(section, 'mount')
    run_command(f'{mount_cmd} {device} {mnt}')

def results_to_dict(run, include_time=False):
    ret_dict = {}
    sub_results = list(itertools.chain(run.time_results, run.fio_results,
                                       run.dbench_results))
    for r in sub_results:
        for k in vars(r):
            if not isinstance(getattr(r, k), numbers.Number):
                continue
            if "id" in k:
                continue
            ret_dict[k] = getattr(r, k)
    if include_time:
        ret_dict['time'] = run.time
    return ret_dict

def avg_results(results):
    ret_dict = {}
    nr = 0
    vals_dict = {}
    for run in results:
        sub_results = results_to_dict(run)
        for k,v in sub_results.items():
            if k not in vals_dict:
                vals_dict[k] = [v]
            else:
                vals_dict[k].append(v)
    for k,v in vals_dict.items():
        if len(v) == 1:
            ret_dict[k] = {}
            ret_dict[k]['mean'] = v[0]
            ret_dict[k]['stdev'] = 0
            continue
        mean = statistics.mean(v)
        stddev = statistics.stdev(v)
        ret_dict[k] = {}
        loop = 1
        while loop:
            loop = 0
            for val in v:
                if stddev == 0:
                    break
                zval = (val - mean) / stddev
                if zval > 3 or zval < -3:
                    v.remove(val)
                    loop = 1
        ret_dict[k]['mean'] = statistics.mean(v)
        ret_dict[k]['stdev'] = statistics.stdev(v)
    return ret_dict

def pct_diff(a, b):
    if a == 0:
        return 0
    return ((b - a) / a) * 100

def diff_string(a, b, better):
    OK = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    diff = pct_diff(a['mean'], b['mean'])
    if better == HIGHER_IS_BETTER:
        threshold = a['mean'] - (a['stdev'] * 1.96)
        if b['mean'] < threshold:
            return FAIL + "{:.2f}%".format(diff) + ENDC
    else:
        threshold = a['mean'] + (a['stdev'] * 1.96)
        if b['mean'] > threshold:
            return FAIL + "{:.2f}%".format(diff) + ENDC
    return OK + "{:.2f}%".format(diff) + ENDC

def check_regression(baseline, recent):
    nr_regress_keys = 0
    nr_fail = 0
    for k,v in baseline.items():
        better = HIGHER_IS_BETTER
        if k in value_mapping:
            better = value_mapping[k]
        if k in test_regression_keys:
            nr_regress_keys += 1
        if better == HIGHER_IS_BETTER:
            threshold = v['mean'] - (v['stdev'] * 1.96)
            if recent[k]['value'] < threshold:
                recent[k]['regression'] = True
                if k in test_regression_keys:
                    nr_fail += 1
            else:
                recent[k]['regression'] = False
        else:
            threshold = v['mean'] + (v['stdev'] * 1.96)
            if recent[k]['value'] > threshold:
                recent[k]['regression'] = True
                if k in test_regression_keys:
                    nr_fail += 1
            else:
                recent[k]['regression'] = False
    fail_thresh = nr_regress_keys * 10 / 100
    if fail_thresh == 0:
        fail_thresh = 1
    return nr_fail >= fail_thresh

def print_comparison_table(baseline, results):
    table = texttable.Texttable()
    table.set_precision(2)
    table.set_deco(texttable.Texttable.HEADER)
    table.set_cols_dtype(['t', 'a', 'a', 'a', 't'])
    table.set_cols_align(['l', 'r', 'r', 'r', 'r'])
    table_rows = [["metric", "baseline", "current", "stdev", "diff"]]
    for k,v in baseline.items():
        better = HIGHER_IS_BETTER
        if k in value_mapping:
            better = value_mapping[k]
        diff_str = diff_string(v, results[k], better)
        cur = [k, v['mean'], results[k]['mean'], v['stdev'], diff_str]
        table_rows.append(cur)
    table.add_rows(table_rows)
    print(table.draw())

def get_fstype(device):
    fstype = subprocess.check_output("blkid -s TYPE -o value "+device, shell=True)
    # strip the output b'btrfs\n'
    return (str(fstype).removesuffix("\\n'")).removeprefix("b'")

def get_fsid(device):
    fsid = subprocess.check_output("blkid -s UUID -o value "+device, shell=True)
    # Raw output is something like this
    #    b'abcf123f-7e95-40cd-8322-0d32773cb4ec\n'
    # strip off extra characters.
    return str(fsid)[2:38]

def get_readpolicies(device):
    fsid = get_fsid(device)
    sysfs = open("/sys/fs/btrfs/"+fsid+"/read_policy", "r")
    # Strip '[ ]' around the active policy
    policies = (((sysfs.read()).strip()).strip("[")).strip("]")
    sysfs.close()
    return policies

def get_active_readpolicy(device):
    fsid = get_fsid(device)
    sysfs = open("/sys/fs/btrfs/"+fsid+"/read_policy", "r")
    policies = (sysfs.read()).strip()
    # Output is as below, pick the policy within '[ ]'
    #   device [pid] latency
    active = re.search(r"\[([A-Za-z0-9_]+)\]", policies)
    sysfs.close()
    return active.group(1)

def set_readpolicy(device, policy="pid"):
    if not policy in get_readpolicies(device):
        print("Read policy '{}' is invalid".format(policy))
        sys.exit(1)
        return
    fsid = get_fsid(device)
    # Ran out of ideas why run_command fails.
    # command = "echo "+policy+" > /sys/fs/btrfs/"+fsid+"/read_policy"
    # run_command(command)
    sysfs = open("/sys/fs/btrfs/"+fsid+"/read_policy", "w")
    ret = sysfs.write(policy)
    sysfs.close()

def has_readpolicy(device):
    fsid = get_fsid(device)
    return os.path.exists("/sys/fs/btrfs/"+fsid+"/read_policy")
