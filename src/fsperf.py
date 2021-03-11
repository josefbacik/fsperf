import argparse
import configparser
import os
import sys
from subprocess import Popen
import errno
import FioCompare
import ResultData
import PerfTest
from utils import run_command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import importlib.util
import inspect
import datetime
import utils

# Shamelessly copied from stackoverflow
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def run_test(session, config, section, test):
    if config.has_option(section, 'mkfs'):
        run_command(config.get(section, 'mkfs'))
    if config.has_option(section, 'mount'):
        run_command(config.get(section, 'mount'))
    try:
        test.setup()
        test.test(session, config.get(section, 'directory'), "results", section)
    finally:
        if config.has_option(section, 'mount'):
            run_command("umount {}".format(config.get(section, 'directory')))
    return 0

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str,
                    help="Configuration to use to run the tests")
parser.add_argument('-l', '--latency', action='store_true',
                    help="Compare latency values of the current run to old runs")
parser.add_argument('-t', '--testonly', action='store_true',
                    help="Compare this run to previous runs, but do not store this run.")
parser.add_argument('tests', nargs='*',
                    help="Specific test[s] to run.")

args = parser.parse_args()

config = configparser.ConfigParser()
config.read('local.cfg')

disabled_tests = []
failed_tests = []

with open('disabled-tests') as f:
    for line in f:
        disabled_tests.append(line.rstrip())

sections = [args.config]
if args.config is None:
    sections = config.sections()
elif not config.has_section(args.config):
    print("No section '{}' in local.cfg".format(args.config))
    sys.exit(1)

engine = create_engine('sqlite:///fsperf-results.db')
ResultData.Base.metadata.create_all(engine)
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

mkdir_p("results/")

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
    if not config.has_option(s, "directory"):
        print("Must specify a directory option in section {}".format(s))
        sys.exit(1)
    for t in tests:
        if t.__class__.__name__ in disabled_tests:
            print("Skipping {}".format(t.__class__.__name__))
            continue
        if len(args.tests) and t.name not in args.tests:
            continue
        print("Running {}".format(t.__class__.__name__))
        run_test(session, config, s, t)

if args.testonly:
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    for t in tests:
        if len(args.tests) and t.name not in args.tests:
            continue
        results = session.query(ResultData.Run).\
                outerjoin(ResultData.FioResult).\
                outerjoin(ResultData.DbenchResult).\
                outerjoin(ResultData.TimeResult).\
                filter(ResultData.Run.time >=week_ago).\
                filter(ResultData.Run.name == t.name).\
                order_by(ResultData.Run.id).all()
        newest = results.pop()
        cur = utils.results_to_dict(newest)
        avg_results = utils.avg_results(results)
        utils.print_comparison_table(avg_results, cur)
        session.delete(newest)
        session.commit()
