from PerfTest import FioTest

class Dio4kbs16threads(FioTest):
    name = "dio4kbs16threads"
    command = ("--name dio4kbs16threads --direct=1 --size=1g --rw=randwrite "
               "--norandommap --runtime=60 --iodepth=1024 --nrfiles=16 "
               "--numjobs=16")
