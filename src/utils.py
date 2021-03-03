from subprocess import Popen
import sys

def run_command(cmd):
    print("  running cmd '{}'".format(cmd))
    devnull = open('/dev/null')
    p = Popen(cmd.split(' '), stdout=devnull, stderr=devnull)
    p.wait()
    devnull.close()
    if p.returncode == 0:
        return
    print("Command '{}' failed to run".format(cmd))
    sys.exit(1)
