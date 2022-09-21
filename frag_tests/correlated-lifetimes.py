from PerfTest import FioTest
import os.path

class CorrelatedLifetimes(FioTest):
    name = "correlatedlifetimes"
    command = os.path.join(os.path.dirname(__file__), "correlated-lifetimes.fio")
    trace_fns = "find_free_extent"
