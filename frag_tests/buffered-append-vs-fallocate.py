from PerfTest import FioTest
import os.path

class BufferedAppendVsFallocate(FioTest):
    name = "bufferedappendvsfallocate"
    command = os.path.join(os.path.dirname(__file__), "buffered-append-vs-fallocate.fio")
