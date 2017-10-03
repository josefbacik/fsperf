OK = '\033[92m'
FAIL = '\033[91m'
ENDC = '\033[0m'

default_keys = [ 'iops', 'io_kbytes', 'bw' ]
latency_keys = [ 'lat_ns_min', 'lat_ns_max' ]
io_ops = ['read', 'write', 'trim' ]

def _fuzzy_compare(a, b, fuzzy):
    if a == b:
        return 0
    if a == 0:
        return 100
    a = float(a)
    b = float(b)
    fuzzy = float(fuzzy)
    val = ((b - a) / a) * 100
    if val > fuzzy or val < -fuzzy:
        return val;
    return 0

def _compare_jobs(ijob, njob, latency, fuzz):
    failed = 0
    for k in default_keys:
        for io in io_ops:
            key = "{}_{}".format(io, k)
            comp = _fuzzy_compare(ijob[key], njob[key], fuzz)
            if comp < 0:
                outstr =  "    {} regressed: old {} new {} {}%".format(key,
                            ijob[key], njob[key], comp)
                print(FAIL + outstr + ENDC)
                failed += 1
            elif comp > 0:
                outstr = "    {} improved: old {} new {} {}%".format(key,
                            ijob[key], njob[key], comp)
                print(OK + outstr + ENDC)
    for k in latency_keys:
        if not latency:
            break
        for io in io_ops:
            key = "{}_{}".format(io, k)
            comp = _fuzzy_compare(ijob[key], njob[key], fuzz)
            if comp > 0:
                outstr =  "    {} regressed: old {} new {} {}%".format(key,
                            ijob[key], njob[key], comp)
                print(FAIL + outstr + ENDC)
                failed += 1
            elif comp < 0:
                outstr = "    {} improved: old {} new {} {}%".format(key,
                            ijob[key], njob[key], comp)
                print(OK + outstr + ENDC)
    k = 'sys_cpu'
    comp = _fuzzy_compare(ijob[k], njob[k], fuzz)
    if comp > 0:
        outstr =  "    sys_cpu regressed: old {} new {} {}%".format(ijob[k],
                    njob[k], comp)
        print(FAIL + outstr + ENDC)
        failed += 1
    elif comp < 0:
        outstr =  "    sys_cpu improved: old {} new {} {}%".format(ijob[k],
                    njob[k], comp)
        print(OK + outstr + ENDC)
    return failed

def compare_individual_jobs(initial, data, fuzz):
    failed = 0;
    initial_jobs = initial['jobs'][:]
    for njob in data['jobs']:
        for ijob in initial_jobs:
            if njob['jobname'] == ijob['jobname']:
                print("  Checking results for {}".format(njob['jobname']))
                failed += _compare_jobs(ijob, njob, fuzz)
                initial_jobs.remove(ijob)
                break
    return failed

def default_merge(data):
    '''Default merge function for multiple jobs in one run

    For runs that include multiple threads we will have a lot of variation
    between the different threads, which makes comparing them to eachother
    across multiple runs less that useful.  Instead merge the jobs into a single
    job.  This function does that by adding up 'iops', 'io_kbytes', and 'bw' for
    read/write/trim in the merged job, and then taking the maximal values of the
    latency numbers.
    '''
    merge_job = {}
    merge_job['sys_cpu'] = 0.0
    for job in data['jobs']:
        merge_job['sys_cpu'] += job['sys_cpu']
        for io in io_ops:
            for k in default_keys:
                key = "{}_{}".format(io, k)
                if key not in merge_job:
                    merge_job[key] = job[key]
                else:
                    merge_job[key] += job[key]
            for k in latency_keys:
                key = "{}_{}".format(io, k)
                if key not in merge_job:
                    merge_job[key] = job[key]
                elif merge_job[key] < job[key]:
                    merge_job[key] = job[key]
    return merge_job

def compare_fiodata(initial, data, latency, merge_func=default_merge, fuzz=5):
    failed  = 0
    if merge_func is None:
        return compare_individual_jobs(initial, data, fuzz)
    ijob = merge_func(initial)
    njob = merge_func(data)
    return _compare_jobs(ijob, njob, latency, fuzz)
