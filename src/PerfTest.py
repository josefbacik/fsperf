import FioResultDecoder
import ResultData
import utils
import json
from timeit import default_timer as timer

class PerfTest():
    name = ""
    command = ""

    def setup(self):
        pass
    def test(self, run, directory, results):
        pass

class FioTest(PerfTest):
    def record_results(self, run, results):
        json_data = open("{}/{}.json".format(results, self.name))
        data = json.load(json_data, cls=FioResultDecoder.FioResultDecoder)
        for j in data['jobs']:
            r = ResultData.FioResult()
            r.load_from_dict(j)
            run.fio_results.append(r)

    def test(self, run, directory, results):
        command = "fio --output-format=json"
        command += " --output={}/{}.json".format(results, self.name)
        command += " --alloc-size 98304 --allrandrepeat=1"
        command += " --directory {} ".format(directory)
        command += self.command
        utils.run_command(command)

        self.record_results(run, results)

class TimeTest(PerfTest):
    def record_results(self, run, elapsed):
        r = ResultData.TimeResult()
        r.elapsed = elapsed
        run.time_results.append(r)

    def test(self, run, directory, results):
        command = self.command.replace('DIRECTORY', directory)
        start = timer()
        utils.run_command(command)
        elapsed = timer() - start
        self.record_results(run, elapsed)

class DbenchTest(PerfTest):
    def record_results(self, run, result_dict):
        r = ResultData.DbenchResult()
        r.load_from_dict(result_dict)
        run.dbench_results.append(r)

    def test(self, run, directory, results):
        command = "dbench " + self.command + " -D {}".format(directory)
        fd = open("{}/{}.txt".format(results, self.name), "w+")
        utils.run_command(command, fd)
        fd.seek(0)
        parse = False
        results = {}
        for line in fd:
            if not parse:
                if "----" in line:
                    parse = True
                continue
            vals = line.split()
            if len(vals) == 4:
                key = vals[0].lower()
                results[key] = vals[3]
            elif len(vals) > 4:
                results['throughput'] = vals[1]
        self.record_results(run, results)
