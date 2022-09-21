from PerfTest import FioTest
import os.path

class FunnySizesLow(FioTest):
    name = "funnysizeslow"
    command = os.path.join(os.path.dirname(__file__), "funny-sizes-low.fio")
    trace_fns = "find_free_extent"
