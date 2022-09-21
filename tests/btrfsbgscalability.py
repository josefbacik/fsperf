from PerfTest import FioTest
from nullblk import NullBlock
import utils

class BtrfsBgScalability(FioTest):
    name = "btrfsbgscalability"
    command = ("--name btrfsbgscalability --rw=randwrite --fsync=0 "
               "--fallocate=posix --group_reporting --direct=1 "
               "--ioengine=io_uring --iodepth=64 --bs=64k --filesize=1g "
               "--runtime=300 --time_based --numjobs=8 --thread")
    oneoff = True
    skip_mkfs_and_mount = True

    def teardown(self, config, results):
        directory = config.get('main', 'directory')
        self.mnt.umount()
        self.nullb_mnt.umount()
        utils.run_command(f'umount {directory}')
        self.nullblk = None

    def setup(self, config, section):
        directory = config.get('main', 'directory')
        self.nullblk = NullBlock()
        config_values = { 'submit_queues': '2',
                          'size': '16384',
                          'memory_backed': '1',
                        }
        self.nullblk.config_values = config_values
        try:
            self.nullblk.start()
        except:
            raise utils.NotRunException("We don't have nullblk support loaded")

        mkfsopts = "-f -R free-space-tree -O no-holes"
        mntcmd = "mount -o ssd,nodatacow"

        # First create the nullblk fs to load the loop device onto
        command = f'mkfs.btrfs {mkfsopts} /dev/nullb0'
        utils.run_command(command)
        self.nullb_mnt = utils.Mount(mntcmd, '/dev/nullb0', directory)

        # Now create the loop device
        loopdir = f'{directory}/loop'
        loopfile = f'{directory}/loopfile'
        utils.mkdir_p(f'{directory}/loop')
        utils.run_command(f'truncate -s 4T {loopfile}')
        utils.run_command(f'mkfs.btrfs {mkfsopts} {loopfile}')
        self.mnt = utils.Mount(mntcmd, loopfile, loopdir)

        # Trigger the allocation of about 3500 data block groups, without
        # actually consuming space on the underlying filesystem, just to make
        # the tree of block groups large
        utils.run_command(f'fallocate -l 3500G {loopdir}/filler')

    # We override test here just because we create a loopback device ontop of
    # the directory and want to use a different directory than the one we
    # mounted the nullblk ontop of
    def test(self, run, config, results):
        directory = self.mnt.mount_point
        command = self.default_cmd(results)
        command += f' --directory {directory} '
        command += self.command
        utils.run_command(command)

        self.record_results(run, results)
