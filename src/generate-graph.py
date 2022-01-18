from ResultData import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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

def get_all_purposes(session):
    r = session.query(Run.purpose).distinct().all()
    results = []
    for i in r:
        results.append(i[0])
    return results

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--test', type=str, required=True,
                    help="Test to generate the graph for")
parser.add_argument('-d', '--dir', type=str, default=".",
                    help="Directory to write the graphs to")
args = parser.parse_args()

engine = create_engine('sqlite:///fsperf-results.db')
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
formatter = mdates.ConciseDateFormatter(locator)

purposes = get_all_purposes(session)

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
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    datemin = None
    datemax = None
    for p in purposes:
        print(f'getting results for {p}')
        results = get_all_results(session, p, args.test)
        (dates, values) = utils.get_values_for_key(results, k)
        if dates is None:
            continue

        # figure out the range
        curmin = np.datetime64(dates[0], 'D')
        curmax = np.datetime64(dates[-1], 'D') + 1
        if not datemin or curmin < datemin:
            datemin = curmin
        if not datemax or curmax > datemax:
            datemax = curmax
        plt.plot(dates, values, label=p)

    ax.set_xlim(datemin, datemax)
    fig.autofmt_xdate()
    plt.title(f"{args.test} results over time")
    plt.legend(bbox_to_anchor=(1.04, 1), borderaxespad=0)
    plt.savefig(f"{args.dir}/{args.test}_{k}.png", bbox_inches="tight")
    plt.close('all')
