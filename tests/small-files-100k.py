from PerfTest import FioTest

class SmallFiles100k(FioTest):
    name = "smallfiles100k"
    command = ("--name=smallfiles100k --nrfiles=100000 --blocksize_unaligned=1 "
               "--filesize=10:1m --readwrite=write --fallocate=none --numjobs=4 "
               "--create_on_open=1 --group_reporting=1 --openfiles=500")
