from PerfTest import FioTest

class BufferedRandwrite16g(FioTest):
    name = "bufferedrandwrite16g"
    command = ("--name bufferedrandwrite16g --allrandrepeat=1 "
               "--readwrite randwrite --size 16G --ioengine psync "
               "--end_fsync 1 --fallocate none")
