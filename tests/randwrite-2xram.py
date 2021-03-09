from PerfTest import FioTest
import psutil

class Randwrite2xRam(FioTest):
    name = "randwrite2xram"
    command = ("--name randwrite2xram --direct=0 --ioengine=sync --thread "
               "--invalidate=1 --group_reporting=1 --runtime=300 "
               "--fallocate=none --ramp_time=10 --new_group --rw=randwrite "
               "--size=SIZE --numjobs=4 --bs=4k --fsync_on_close=0 "
               "--end_fsync=0")

    def setup(self):
        mem = psutil.virtual_memory()
        self.command = self.command.replace('SIZE', str(mem.total*2))
