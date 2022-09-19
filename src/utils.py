from subprocess import Popen, PIPE, DEVNULL, CalledProcessError
import PerfTest
import ResultData
import sys
import os
import errno
import texttable
import itertools
import datetime
import statistics
import subprocess
import re
import shlex
import collections
import importlib.util
import inspect

LOWER_IS_BETTER = 0
HIGHER_IS_BETTER = 1

METRIC_DIRECTIONS = {
    'elapsed': LOWER_IS_BETTER,
    'sys_cpu': LOWER_IS_BETTER,
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

def metric_direction(metric):
    if "bytes" in metric:
        return HIGHER_IS_BETTER
    if "calls" in metric:
        return LOWER_IS_BETTER
    if "_iops" in metric:
        return HIGHER_IS_BETTER
    if "_ns_" in metric:
        return LOWER_IS_BETTER
    if metric in METRIC_DIRECTIONS:
        return METRIC_DIRECTIONS[metric]
    return LOWER_IS_BETTER


# We only mark the whole test as failed if these keys regress
test_regression_keys = [
    'read_bw_bytes',
    'write_bw_bytes',
    'throughput',
    'elapsed'
]

class NotRunException(Exception):
    def __init__(self, m):
        super().__init__(m)
        self.m = m

def get_last_test(session, test):
    result = session.query(ResultData.Run).\
        outerjoin(ResultData.FioResult).\
        outerjoin(ResultData.DbenchResult).\
        outerjoin(ResultData.TimeResult).\
        filter(ResultData.Run.name == test).\
        order_by(ResultData.Run.id.desc()).first()
    return results_to_dict(result)

def get_results(session, name, config, purpose, time):
    return session.query(ResultData.Run).\
                outerjoin(ResultData.FioResult).\
                outerjoin(ResultData.DbenchResult).\
                outerjoin(ResultData.TimeResult).\
                outerjoin(ResultData.Fragmentation).\
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
    if not outputfile:
        outputfile = DEVNULL
    p = Popen(shlex.split(cmd), stdout=outputfile, stderr=outputfile)
    p.wait()
    if p.returncode:
        raise CalledProcessError(p.returncode, cmd)

def setup_cpu_governor(config):
    if not config.has_option('main', 'cpugovernor'):
        return
    governor = config.get('main', 'cpugovernor')
    dirpath = "/sys/devices/system/cpu"
    for filename in os.listdir(dirpath):
        if re.match("cpu\d+", filename):
            try:
                with open(f'{dirpath}/{filename}/cpufreq/scaling_governor', 'w') as f:
                    f.write(governor)
            except OSError as exc:
                print("cpu governor isn't enabled, skipping")
                return

def setup_device(config, section):
    device = os.path.basename(os.path.realpath(config.get(section, 'device')))
    if config.has_option(section, 'iosched'):
        with open(f'/sys/block/{device}/queue/scheduler', 'w') as f:
            f.write(config.get(section, 'iosched'))

def want_mkfs(test, config, section):
    return not test.skip_mkfs_and_mount and config.has_option(section, 'mkfs')

def mkfs(test, config, section):
    if not want_mkfs(test, config, section):
        return
    device = config.get(section, 'device')
    mkfs_cmd = config.get(section, 'mkfs')
    run_command(f'{mkfs_cmd} {device}')

def want_mnt(test, config, section):
    return config.has_option(section, 'mount') and not test.skip_mkfs_and_mount

class Mount:
    def __init__(self, test, config, section):
        self.live = False
        if want_mnt(test, config, section):
            self.want_mnt = True
            self.mount_cmd = config.get(section, 'mount')
            self.device = config.get(section, 'device')
            self.mnt = config.get('main', 'directory')

    def do_mount(self):
        if self.want_mnt:
            run_command(f'{self.mount_cmd} {self.device} {self.mnt}')
            self.live = True

    def do_umount(self):
        if self.live:
            run_command(f"umount {self.mnt}")

    def cycle_mount(self):
        self.do_umount()
        self.do_mount()

    def __enter__(self):
        self.do_mount()
        return self

    def __exit__(self, et, ev, etb):
        self.do_umount()
        # re-raise
        if et is not None:
            return False

def results_to_dict(run, include_time=False):
    ret_dict = {}
    sub_results = list(itertools.chain(run.time_results, run.fio_results,
                                       run.dbench_results, run.fragmentation))
    for r in sub_results:
        ret_dict.update(r.to_dict())
    if include_time:
        ret_dict['time'] = run.time
    return ret_dict

def filter_outliers(vs, mean, stdev):
    def z(v, mean, stdev):
        if not stdev or not mean:
            return 0
        return (v - mean) / stdev
    return [v for v in vs if abs(z(v, mean, stdev)) > 3]

def avg_results(results):
    ret_dict = {}
    vals_dict = collections.defaultdict(list)
    for run in results:
        run_results = results_to_dict(run)
        for k,v in run_results.items():
            vals_dict[k].append(v)
    for k,vs in vals_dict.items():
        ret_dict[k] = {}
        if len(vs) == 1:
            ret_dict[k]['mean'] = vs[0]
            ret_dict[k]['stdev'] = 0
            continue
        mean = statistics.mean(vs)
        stdev = statistics.stdev(vs)
        filtered = filter_outliers(vs, mean, stdev)
        ret_dict[k]['mean'] = statistics.mean(vs)
        ret_dict[k]['stdev'] = statistics.stdev(vs)
    return ret_dict

def pct_diff(a, b):
    if a == 0:
        return 0
    return ((b - a) / a) * 100

def color_str(s, color):
    ENDC = '\033[0m'
    return color + s + ENDC

def diff_string(a, b, better):
    DEFAULT = '\033[99m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    sig_delta = a['stdev'] * 1.96
    lo_thresh = a['mean'] - sig_delta
    hi_thresh = a['mean'] + sig_delta
    below = b['mean'] < lo_thresh
    above = b['mean'] > hi_thresh
    higher_better = better == HIGHER_IS_BETTER

    bad = (below and higher_better) or (above and not higher_better)
    good = (above and higher_better) or (below and not higher_better)
    if bad:
        color = RED
    elif good:
        color = GREEN
    else:
        color = DEFAULT

    diff = pct_diff(a['mean'], b['mean'])
    diff_str = "{:.2f}%".format(diff)
    return color_str(diff_str, color)

def check_regression(baseline, recent):
    nr_regress_keys = 0
    nr_fail = 0
    for k,v in baseline.items():
        better = metric_direction(k)
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
    table = texttable.Texttable(max_width=100)
    table.set_precision(2)
    table.set_deco(texttable.Texttable.HEADER)
    table.set_cols_dtype(['t', 'a', 'a', 'a', 't'])
    table.set_cols_align(['l', 'r', 'r', 'r', 'r'])
    table_rows = [["metric", "baseline", "current", "stdev", "diff"]]
    for k,v in sorted(baseline.items()):
        if not v['mean']:
            continue
        if k not in results:
            continue
        better = metric_direction(k)
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

def get_tests(test_dir):
    tests = []
    oneoffs = []
    for (dirpath, dirnames, filenames) in os.walk(test_dir):
        for f in filenames:
            if not f.endswith(".py"):
                continue
            p = dirpath + '/' + f
            spec = importlib.util.spec_from_file_location('module.name', p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            attrs = set(dir(m)) - set(dir(PerfTest))
            for cname in attrs:
                c = getattr(m, cname)
                if inspect.isclass(c) and issubclass(c, PerfTest.PerfTest):
                    t = c()
                    if t.oneoff:
                        oneoffs.append(t)
                    else:
                        tests.append(t)
    return tests, oneoffs
