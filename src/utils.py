from subprocess import Popen
import sys
import os
import errno
import texttable
import itertools
import numbers
import datetime

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
    for run in results:
        sub_results = results_to_dict(run)
        for k,v in sub_results.items():
            if k not in ret_dict:
                ret_dict[k] = v
            else:
                ret_dict[k] += v
        nr += 1
    for k,v in ret_dict.items():
        ret_dict[k] = v / nr
    return ret_dict

def pct_diff(a, b):
    if a == 0:
        return 0
    return ((b - a) / a) * 100

def diff_string(a, b, better):
    OK = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    diff = pct_diff(a, b)
    if better == HIGHER_IS_BETTER:
        if -diff >=  5.0:
            return FAIL + "{:.2f}%".format(diff) + ENDC
    else:
        if diff >= 5.0:
            return FAIL + "{:.2f}%".format(diff) + ENDC
    return OK + "{:.2f}%".format(diff) + ENDC

def check_regression(baseline, recent, threshold):
    fail_thresh = len(baseline.items()) * 10 / 100
    if fail_thresh == 0:
        fail_thresh = len(baseline.items())
    nr_fail = 0
    for k,v in baseline.items():
        diff = pct_diff(v, recent[k]['value'])
        better = HIGHER_IS_BETTER
        if k in value_mapping:
            better = value_mapping[k]
        if better == HIGHER_IS_BETTER:
            if -diff > threshold:
                recent[k]['regression'] = True
                nr_fail += 1
            else:
                recent[k]['regression'] = False
        else:
            if diff > threshold:
                recent[k]['regression'] = True
                nr_fail += 1
            else:
                recent[k]['regression'] = False
    return nr_fail >= fail_thresh

def print_comparison_table(baseline, results):
    table = texttable.Texttable()
    table.set_precision(2)
    table.set_deco(texttable.Texttable.HEADER)
    table.set_cols_dtype(['t', 'a', 'a', 't'])
    table.set_cols_align(['l', 'r', 'r', 'r'])
    table_rows = [["metric", "baseline", "current", "diff"]]
    for k,v in baseline.items():
        better = HIGHER_IS_BETTER
        if k in value_mapping:
            better = value_mapping[k]
        diff_str = diff_string(v, results[k], better)
        cur = [k, v, results[k], diff_str]
        table_rows.append(cur)
    table.add_rows(table_rows)
    print(table.draw())
