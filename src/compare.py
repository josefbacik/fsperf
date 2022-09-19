import ResultData

import argparse
import configparser
import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import utils

def compare_results(session, section_A, section_B, test, purpose_A, purpose_B, age):
    results_A = utils.get_results(session, test.name, section_A, purpose_A, age)
    results_B = utils.get_results(session, test.name, section_B, purpose_B, age)
    avg_A = utils.avg_results(results_A)
    avg_B = utils.avg_results(results_B)
    print(f"{test.name} results")
    utils.print_comparison_table(avg_A, avg_B)
    print("")

if __name__ == "__main__":
    engine = create_engine('sqlite:///fsperf-results.db')
    ResultData.Base.metadata.create_all(engine)
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()

    parser = argparse.ArgumentParser()
    parser.add_argument('A', type=str, help='purpose A for a comparison')
    parser.add_argument('B', type=str, help='purpose B for a comparison')
    parser.add_argument('-F', '--fragmentation', action='store_true', help='include fragmentation tests')
    
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('local.cfg')
    sections = config.sections()
    sections.remove("main")
    
    tests, oneoffs = utils.get_tests("tests/")
    if args.fragmentation:
        frag_tests, _ = utils.get_tests("frag_tests/")
        tests.extend(frag_tests)

    age = datetime.date.today() - datetime.timedelta(days=365)

    for section in sections:
        print(f"{section} test results")
        for test in tests:
            compare_results(session, section, section, test, args.A, args.B, age)
