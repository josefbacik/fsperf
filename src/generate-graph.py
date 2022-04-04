from ResultData import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse
import matplotlib.pyplot as plt
import numpy as np
import datetime
import utils
import numbers

def get_all_results(session, purpose, test):
    results = session.query(Run).\
        outerjoin(FioResult).\
        outerjoin(DbenchResult).\
        outerjoin(TimeResult).\
        filter(Run.name == test).\
        filter(Run.purpose == purpose).\
        order_by(Run.time).all()
    ret = []
    for r in results:
        ret.append(utils.results_to_dict(r, include_time=True))
    return ret

def get_all_purposes(session, purposes):
    r = session.query(Run.purpose).distinct().all()
    results = []
    for i in r:
        if len(purposes) == 0 or i[0] in purposes:
            results.append(i[0])
    return results

def get_values_for_key(results_array, key):
    runs = []
    values = []
    found_nonzero = False
    count = 0
    for run in results_array:
        runs.append(count)
        count += 1
        values.append(run[key])
        if run[key] > 0 or run[key] < 0:
            found_nonzero = True
    if found_nonzero:
        return (runs, values)
    return (None, None)

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--test', type=str, required=True,
                    help="Test to generate the graph for")
parser.add_argument('-d', '--dir', type=str, default=".",
                    help="Directory to write the graphs to")
parser.add_argument('-p', '--purposes', nargs="*", type=str, default=[],
                    help="Purposes to graph")

args = parser.parse_args()

engine = create_engine('sqlite:///fsperf-results.db')
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

purposes = get_all_purposes(session, args.purposes)

last = utils.get_last_test(session, args.test)
for k,v in last.items():
    if not isinstance(v, numbers.Number):
        continue
    if "id" in k:
        continue
    if v == 0:
        continue

    print(f'Generating graph for {args.test}_{k}')
    # Start a new figure
    plt.figure()
    fig, ax = plt.subplots()

    # format the ticks
    #ax.xaxis.set_major_locator(locator)
    #ax.xaxis.set_major_formatter(formatter)

    for p in purposes:
        print(f'getting results for {p}')
        results = get_all_results(session, p, args.test)
        (runs, values) = get_values_for_key(results, k)
        if runs is None:
            continue

        plt.plot(runs, values, label=p)

    plt.title(f"{args.test} {k} results over time")
    plt.legend(bbox_to_anchor=(1.04, 1), borderaxespad=0)
    plt.show()
    plt.savefig(f"{args.dir}/{args.test}_{k}.png", bbox_inches="tight")
    plt.close('all')
