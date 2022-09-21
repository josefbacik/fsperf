import argparse
import configparser
import os
import sys
from subprocess import Popen
import FioCompare
import ResultData
from utils import run_command,Mount,setup_device,setup_cpu_governor,mkfs,NotRunException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
import utils
import compare
import platform

TEST_ONLY = "TMP-TEST-ONLY"

def clean_testonly(session, sections, tests):
    today = datetime.date.today()
    age = today - datetime.timedelta(days=365)
    for section in sections:
        for test in tests:
            results = utils.get_results(session, test.name, section, TEST_ONLY, age)
            for r in results:
                session.delete(r)
    session.commit()

def want_run_test(run_tests, disabled_tests, t):
    names = [t.name, t.__class__.__name__]
    if disabled_tests:
        for name in names:
            if name in disabled_tests:
                print(f"{name} disabled!")
                return False
    if run_tests:
        for name in names:
            if name in run_tests:
                print(f"{name} enabled!")
                return True
        print(f"{names} are not explicitly enabled ({run_tests})")
        return False
    return True

def run_test(args, session, config, section, purpose, test):
    for i in range(0, args.numruns):
        try:
            run = ResultData.Run(kernel=platform.release(), config=section,
                                 name=test.name, purpose=purpose)
            test.run(run, config, section, "results")
            session.add(run)
            session.commit()
        except NotRunException as e:
            print("Not run: {}".format(e))
    return 0

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str,
                    help="Configuration to use to run the tests")
parser.add_argument('-l', '--latency', action='store_true',
                    help="Compare latency values of the current run to old runs")
parser.add_argument('-t', '--testonly', action='store_true',
                    help="Compare this run to previous runs, but do not store this run.")
parser.add_argument('-F', '--fragmentation', action='store_true',
                    help="include fragmentation tests in run")
parser.add_argument('-n', '--numruns', type=int, default=1,
                    help="Run each test N number of times")
parser.add_argument('-p', '--purpose', type=str, default="continuous",
                    help="Set the specific purpose for this run, useful for A/B testing")
parser.add_argument('-C', '--compare', type=str,
                    help="Configuration to compare this run to, used with -t")
parser.add_argument('tests', nargs='*',
                    help="Specific test[s] to run.")
parser.add_argument('--list', action='store_true', help="List all available tests")

args = parser.parse_args()

config = configparser.ConfigParser()
config.read('local.cfg')
if not config.has_section('main'):
    print("Must have a [main] section in local.cfg")
    sys.exit(1)

if not config.get('main', 'directory'):
    print("Must specify 'directory' in [main]")
    sys.exit(1)

setup_cpu_governor(config)

disabled_tests = []
failed_tests = []

try:
    with open('disabled-tests') as f:
        for line in f:
            disabled_tests.append(line.rstrip())
            print("Disabled {}".format(line.rstrip()))
except FileNotFoundError:
    pass

sections = [args.config]
if args.config is None:
    sections = config.sections()
    sections.remove('main')
elif not config.has_section(args.config):
    print("No section '{}' in local.cfg".format(args.config))
    sys.exit(1)

compare_config = None
if args.compare is not None:
    compare_config = args.compare
    if not config.has_section(compare_config):
        print("No section '{}' in local.cfg".format(compare_config))
        sys.exit(1)

engine = create_engine('sqlite:///fsperf-results.db')
ResultData.Base.metadata.create_all(engine)
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

utils.mkdir_p("results/")

tests, oneoffs = utils.get_tests("tests/")

if args.fragmentation:
    frag_tests, frag_oneoffs = utils.get_tests("frag_tests/")
    tests.extend(frag_tests)
    oneoffs.extend(frag_oneoffs)

if args.list:
    print("Normal tests")
    for t in tests:
        print("\t{}".format(t.__class__.__name__))
    print("Oneoff tests")
    for t in oneoffs:
        print("\t{}".format(t.__class__.__name__))
    sys.exit(1)

if args.testonly:
    run_purpose = TEST_ONLY
    # We might have exited uncleanly and left behind testonly results
    clean_testonly(session, sections, tests)
else:
    run_purpose = args.purpose

# Run the normal tests
for section in sections:
    setup_device(config, section)
    for t in tests:
        if not want_run_test(args.tests, disabled_tests, t):
            continue
        print("Running {}".format(t.__class__.__name__))
        run_test(args, session, config, section, run_purpose, t)

for t in oneoffs:
    if not want_run_test(args.tests, disabled_tests, t):
        continue
    print("Running {}".format(t.__class__.__name__))
    run_test(args, session, config, "oneoff", run_purpose, t)

if args.testonly:
    today = datetime.date.today()
    if args.purpose == "continuous":
        age = today - datetime.timedelta(days=7)
    else:
        age = today - datetime.timedelta(days=365)
    for section in sections:
        print(f"{section} test results")
        for t in tests:
            if not want_run_test(args.tests, disabled_tests, t):
                print(f'skipping test {t.name}')
                continue
            compare_section = compare_config if compare_config else section
            compare.compare_results(session, compare_section, section, t, args.purpose, TEST_ONLY, age)
    # We use the db to uniformly access test results. Clean up testonly results
    clean_testonly(session, sections, tests)
