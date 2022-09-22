import FioResultDecoder
import ResultData
import utils
import json
from timeit import default_timer as timer
import contextlib

RESULTS_DIR = "results"
FRAG_DIR = "src/frag"

class PerfTest:
    name = ""
    command = ""
    trace_fns = ""
    need_remount_after_setup = False
    skip_mkfs_and_mount = False
    end_state_umount_s = 0
    end_state_mount_s = 0

    # Set this if the test does something specific and isn't going to use the
    # configuration options to change how the test is run.
    oneoff = False

    def maybe_cycle_mount(self, mnt):
        if self.need_remount_after_setup:
            mnt.cycle_mount()

    def run(self, run, config, section, results):
        with self.test_context(config, section):
            self.maybe_cycle_mount(self.mnt)
            with utils.LatencyTracing(self.what_latency_traces(config, section)) as lt:
                self.test(run, config, results)
            self.latency_traces = lt.results()
            self.collect_fragmentation(run, config)
            self.commit_stats = utils.collect_commit_stats(config, section, run)
            self.end_state_umount_s, self.end_state_mount_s = self.mnt.timed_cycle_mount()
            self.record_results(run)

    # do generic setup (mkfs/mount), then test-specific setup.
    # use ExitStack to ensure we call umount/teardown appropriately
    def test_context(self, config, section):
        utils.mkfs(self, config, section)
        stack = contextlib.ExitStack()
        if utils.want_mnt(self, config, section):
            self.mnt = utils.Mount(
                    config.get(section, 'mount'),
                    config.get(section, 'device'),
                    config.get('main', 'directory'))
            stack.enter_context(self.mnt)
        self.setup(config, section)
        stack.callback(self.teardown, config, RESULTS_DIR)
        return stack

    # override for special per-test setup
    def setup(self, config, section):
        pass

    def record_results(self, run):
        for lt in self.latency_traces:
            ltr = ResultData.LatencyTrace()
            ltr.load_from_dict(lt)
            run.latency_traces.append(ltr)
        mt = ResultData.MountTiming(self.end_state_umount_s, self.end_state_mount_s)
        run.mount_timings.append(mt)
        f = ResultData.Fragmentation()
        f.load_from_dict(self.fragmentation)
        run.fragmentation.append(f)
        if self.commit_stats and 'commits' in self.commit_stats:
            stats = ResultData.BtrfsCommitStats()
            stats.load_from_dict(self.commit_stats)
            run.btrfs_commit_stats.append(stats)

    # must override, this is the actual test logic!
    def test(self, config):
        raise NotImplementedError

    # override for special per-test teardown (to undo setup)
    def teardown(self, config, results):
        pass

    def collect_fragmentation(self, run, config):
        bg_dump_filename = f"{RESULTS_DIR}/bgs.txt"
        with open(bg_dump_filename, 'w') as f:
            try:
                utils.run_command(f"btrd {FRAG_DIR}/bg-dump.btrd", f)
            except Exception as e:
                print(f"failed to collect fragmentation data: {e}. (Likely, running the btrd script OOMed)")
                self.fragmentation = {}
                return
        frag_filename = f"{RESULTS_DIR}/{self.name}.frag"
        with open(frag_filename, 'w') as f:
            try:
                utils.run_command(f"{FRAG_DIR}/target/release/btrfs-frag-view {RESULTS_DIR}/bgs.txt", f)
            except Exception as e:
                print(f"failed to analyze fragmentation data: {e}.")
                self.fragmentation = {}
                return
        self.fragmentation = json.load(open(frag_filename))

    def what_latency_traces(self, config, section):
        trace_fns = ""
        if self.trace_fns:
            trace_fns = self.trace_fns
        elif config.has_option(section, 'trace_fns'):
            trace_fns = config.get(section, 'trace_fns')
        return [fn for fn in trace_fns.split(",") if fn]

class FioTest(PerfTest):
    def record_results(self, run):
        PerfTest.record_results(self, run)
        json_data = open("{}/{}.json".format(RESULTS_DIR, self.name))
        data = json.load(json_data, cls=FioResultDecoder.FioResultDecoder)
        for j in data['jobs']:
            r = ResultData.FioResult()
            r.load_from_dict(j)
            run.fio_results.append(r)

    def default_cmd(self, results):
        command = "fio --output-format=json"
        command += " --output={}/{}.json".format(RESULTS_DIR, self.name)
        command += " --alloc-size 98304 --allrandrepeat=1 --randseed=12345"
        return command

    def test(self, run, config, results):
        directory = config.get('main', 'directory')
        command = self.default_cmd(results)
        command += " --directory {} ".format(directory)
        command += self.command
        utils.run_command(command)

class TimeTest(PerfTest):
    def record_results(self, run):
        PerfTest.record_results(self, run)
        r = ResultData.TimeResult()
        r.elapsed = self.elapsed
        run.time_results.append(r)

    def test(self, run, config, results):
        directory = config.get('main', 'directory')
        command = self.command.replace('DIRECTORY', directory)
        start = timer()
        utils.run_command(command)
        self.elapsed = timer() - start

class DbenchTest(PerfTest):
    def record_results(self, run):
        PerfTest.record_results(self, run)
        r = ResultData.DbenchResult()
        r.load_from_dict(self.results)
        run.dbench_results.append(r)

    def test(self, run, config, results):
        directory = config.get('main', 'directory')
        command = "dbench " + self.command + " -D {}".format(directory)
        fd = open("{}/{}.txt".format(RESULTS_DIR, self.name), "w+")
        utils.run_command(command, fd)
        fd.seek(0)
        parse = False
        self.results = {}
        for line in fd:
            if not parse:
                if "----" in line:
                    parse = True
                continue
            vals = line.split()
            if len(vals) == 4:
                key = vals[0].lower()
                self.results[key] = vals[3]
            elif len(vals) > 4:
                self.results['throughput'] = vals[1]
