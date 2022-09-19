from FragTest import FragTest
import os.path

class BufferedAppendVsFallocate(FragTest):
    name = "bufferedappendvsfallocate"
    command = os.path.join(os.path.dirname(__file__), "buffered-append-vs-fallocate.fio")
