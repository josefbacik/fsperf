from PerfTest import FioTest
import os.path

class MixedLifetimes(FioTest):
    name = "mixedlifetimes"
    command = os.path.join(os.path.dirname(__file__), "mixed-lifetimes.fio")
    trace_fns = "find_free_extent"
