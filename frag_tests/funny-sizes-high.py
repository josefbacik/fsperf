from PerfTest import FioTest
import os.path

class FunnySizesHigh(FioTest):
    name = "funnysizeshigh"
    command = os.path.join(os.path.dirname(__file__), "funny-sizes-high.fio")
    trace_fns = "find_free_extent"
