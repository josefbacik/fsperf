from PerfTest import FioTest

class Bufferedappendsync(FioTest):
    name = "bufferedappenddatasync"
    command = ("--name bufferedappendsync --direct=0 --size=1g --rw=write "
               "--fdatasync=1 --ioengine=sync")
