import argparse
import configparser
import os
import sys
from subprocess import Popen
import FioCompare
import ResultData
import PerfTest
from utils import run_command,mount,setup_device,mkfs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import importlib.util
import inspect
import datetime
import utils
import platform

def run_test(args, session, config, section, test):
    for i in range(0, args.numruns):
        mkfs(config, section)
        mount(config, section)
        try:
            test.setup(config)
            if (test.need_remount_after_setup and
                config.has_option(section, 'mount')):
                run_command("umount {}".format(config.get('main', 'directory')))
                run_command(config.get(section, 'mount'))

            run = ResultData.Run(kernel=platform.release(), config=section,
                                 name=test.name, purpose=args.purpose)
            test.test(run, config, "results")
            session.add(run)
            session.commit()
        finally:
            if config.has_option(section, 'mount'):
                run_command("umount {}".format(config.get('main', 'directory')))
    return 0

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str,
                    help="Configuration to use to run the tests")
parser.add_argument('-l', '--latency', action='store_true',
                    help="Compare latency values of the current run to old runs")
parser.add_argument('-t', '--testonly', action='store_true',
                    help="Compare this run to previous runs, but do not store this run.")
parser.add_argument('-n', '--numruns', type=int, default=1,
                    help="Run each test N number of times")
parser.add_argument('-p', '--purpose', type=str, default="continuous",
                    help="Set the specific purpose for this run, useful for A/B testing")
parser.add_argument('tests', nargs='*',
                    help="Specific test[s] to run.")

args = parser.parse_args()

config = configparser.ConfigParser()
config.read('local.cfg')
if not config.has_section('main'):
    print("Must have a [main] section in local.cfg")
    sys.exit(1)

if not config.get('main', 'directory'):
    print("Must specify 'directory' in [main]")
    sys.exit(1)

disabled_tests = []
failed_tests = []

with open('disabled-tests') as f:
    for line in f:
        disabled_tests.append(line.rstrip())

sections = [args.config]
if args.config is None:
    sections = config.sections()
    sections.remove('main')
elif not config.has_section(args.config):
    print("No section '{}' in local.cfg".format(args.config))
    sys.exit(1)

engine = create_engine('sqlite:///fsperf-results.db')
ResultData.Base.metadata.create_all(engine)
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

utils.mkdir_p("results/")

tests = []
for (dirpath, dirnames, filenames) in os.walk("tests/"):
    for f in filenames:
        if not f.endswith(".py"):
            continue
        p = dirpath + '/' + f
        spec = importlib.util.spec_from_file_location('module.name', p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        attrs = set(dir(m)) - set(dir(PerfTest))
        for cname in attrs:
            c = getattr(m, cname)
            if inspect.isclass(c) and issubclass(c, PerfTest.PerfTest):
                tests.append(c())

for s in sections:
    setup_device(config, s)
    for t in tests:
        if t.__class__.__name__ in disabled_tests:
            print("Skipping {}".format(t.__class__.__name__))
            continue
        if len(args.tests) and t.name not in args.tests:
            continue
        print("Running {}".format(t.__class__.__name__))
        run_test(args, session, config, s, t)

if args.testonly:
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    for s in sections:
        print(f"{s} test results")
        for t in tests:
            if len(args.tests) and t.name not in args.tests:
                continue
            results = session.query(ResultData.Run).\
                    outerjoin(ResultData.FioResult).\
                    outerjoin(ResultData.DbenchResult).\
                    outerjoin(ResultData.TimeResult).\
                    filter(ResultData.Run.time >=week_ago).\
                    filter(ResultData.Run.name == t.name).\
                    filter(ResultData.Run.purpose == args.purpose).\
                    filter(ResultData.Run.config == s).\
                    order_by(ResultData.Run.id).all()
            newest = []
            for i in range(0, args.numruns):
                newest.append(results.pop())
            new_avg = utils.avg_results(newest)
            avg_results = utils.avg_results(results)
            print(f"{t.name} results")
            utils.print_comparison_table(avg_results, new_avg)
            print("")
            for r in newest:
                 session.delete(r)
            session.commit()
