from subprocess import Popen
import sys

def run_command(cmd, outputfile=None):
    print("  running cmd '{}'".format(cmd))
    need_close = False
    if not outputfile:
        outputfile = open('/dev/null')
        need_close = True
    p = Popen(cmd.split(' '), stdout=outputfile, stderr=outputfile)
    p.wait()
    if need_close:
        outputfile.close()
    if p.returncode == 0:
        return
    print("Command '{}' failed to run".format(cmd))
    sys.exit(1)
