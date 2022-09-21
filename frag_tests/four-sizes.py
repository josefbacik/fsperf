from PerfTest import FioTest
import os.path

class FourSizes(FioTest):
    name = "foursizes"
    command = os.path.join(os.path.dirname(__file__), "four-sizes.fio")
    trace_fns = "find_free_extent"
