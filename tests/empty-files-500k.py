from PerfTest import FioTest

class EmptyFiles500k(FioTest):
    name = "emptyfiles500k"
    command = ("--name emptyfiles500k --create_on_open=1 --nrfiles=31250 "
               "--readwrite=write --ioengine=filecreate --fallocate=none "
               "--filesize=4k --openfiles=1")
