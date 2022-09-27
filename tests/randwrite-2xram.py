from PerfTest import FioTest
import psutil
import configparser

class Randwrite2xRam(FioTest):
    name = "randwrite2xram"
    command = ("--name randwrite2xram --direct=0 --ioengine=sync --thread "
               "--invalidate=1 --runtime=300 "
               "--fallocate=none --ramp_time=10 --new_group --rw=randwrite "
               "--size=SIZE --numjobs=4 --bs=BLOCKSIZE --fsync_on_close=0 "
               "--end_fsync=0")

    def setup(self, config, section):
        bs = config.get(section, "blocksize", fallback="4k")
        self.command = Randwrite2xRam.command.replace('BLOCKSIZE', bs)

        mem = psutil.virtual_memory()
        self.command = self.command.replace('SIZE', str((mem.total*2)//4))

