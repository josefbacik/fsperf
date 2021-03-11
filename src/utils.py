from subprocess import Popen
import sys
import texttable
import itertools
import numbers

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

def results_to_dict(run):
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

def diff_string(a, b):
    OK = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    diff = pct_diff(a, b)
    if diff >= 5.0:
        return FAIL + "{:.2f}%".format(diff) + ENDC
    return OK + "{:.2f}%".format(diff) + ENDC

def print_comparison_table(baseline, results):
    table = texttable.Texttable()
    table.set_precision(2)
    table.set_deco(texttable.Texttable.HEADER)
    table.set_cols_dtype(['t', 'a', 'a', 't'])
    table.set_cols_align(['l', 'r', 'r', 'r'])
    table_rows = [["metric", "baseline", "current", "diff"]]
    for k,v in baseline.items():
        diff_str = diff_string(v, results[k])
        cur = [k, v, results[k], diff_str]
        table_rows.append(cur)
    table.add_rows(table_rows)
    print(table.draw())
