import os
import utils

class NullBlock():
    def __del__(self):
        if not self._started:
            return
        dname = f"/sys/kernel/config/nullb/{self.name}"
        with open(f'{dname}/power', 'w') as power:
            power.write('0')
        os.rmdir(dname)

    def __init__(self, name="nullb0"):
        self._started = False
        self.name = name
        self.config_values = {}

    def start(self):
        if not os.path.isdir('/sys/kernel/config/nullb'):
            utils.run_command('modprobe null_blk nr_devices=0')

        if os.path.exists('/dev/nullb0'):
            utils.run_command('rmmod null_blk')
            utils.run_command('modprobe null_blk nr_devices=0')

        dname = f"/sys/kernel/config/nullb/{self.name}"
        os.makedirs(dname)
        for key in self.config_values:
            with open(f"{dname}/{key}", 'w') as writer:
                writer.write(self.config_values[key])
        with open(f"{dname}/power", 'w') as power:
            power.write('1')
        with open(f'/sys/block/{self.name}/queue/scheduler', 'w') as f:
            f.write('none')
        self._started = True
