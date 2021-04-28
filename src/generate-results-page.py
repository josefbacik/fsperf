from ResultData import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jinja2 import Template,Environment,FileSystemLoader
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import datetime
import utils
import numbers

def get_avgs(session, config, test, days):
    today = datetime.date.today()
    thresh = today = datetime.timedelta(days=days)
    results = session.query(Run).\
        outerjoin(FioResult).\
        outerjoin(DbenchResult).\
        outerjoin(TimeResult).\
        filter(Run.time >= thresh).\
        filter(Run.config == config).\
        filter(Run.name == test).\
        filter(Run.purpose == "continuous").\
        order_by(Run.time).all()
    if len(results) > 1:
        newest = results.pop()
    return utils.avg_results(results)

def get_last(session, config, test):
    result = session.query(Run).\
        outerjoin(FioResult).\
        outerjoin(DbenchResult).\
        outerjoin(TimeResult).\
        filter(Run.name == test).\
        filter(Run.config == config).\
        filter(Run.purpose == "continuous").\
        order_by(Run.id.desc()).first()
    results = utils.results_to_dict(result)
    ret = {}
    for k,v in results.items():
        ret[k] = {'value': v}
    return ret

def get_last_test(session, test):
    result = session.query(Run).\
        outerjoin(FioResult).\
        outerjoin(DbenchResult).\
        outerjoin(TimeResult).\
        filter(Run.name == test).\
        filter(Run.purpose == "continuous").\
        order_by(Run.id.desc()).first()
    return utils.results_to_dict(result)

def get_all_results(session, config, test):
    results = session.query(Run).\
        outerjoin(FioResult).\
        outerjoin(DbenchResult).\
        outerjoin(TimeResult).\
        filter(Run.name == test).\
        filter(Run.config == config).\
        filter(Run.purpose == "continuous").\
        order_by(Run.time).all()
    ret = []
    for r in results:
        ret.append(utils.results_to_dict(r, include_time=True))
    return ret

def get_values_for_key(results_array, key):
    dates = []
    values = []
    found_nonzero = False
    for run in results_array:
        dates.append(run['time'])
        values.append(run[key])
        if run[key] > 0 or run[key] < 0:
            found_nonzero = True
    if found_nonzero:
        return (dates, values)
    return (None, None)

engine = create_engine('sqlite:///fsperf-results.db')
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

tests = []
for tname in session.query(Run.name).distinct():
    tests.append(tname[0])

configs = []
for config in session.query(Run.config).distinct():
    configs.append(config[0])

week_avgs = {}
two_week_avgs = {}
three_week_avgs = {}
four_week_avgs = {}
recent = {}

for c in configs:
    recent[c] = {}
    week_avgs[c] = {}
    two_week_avgs[c] = {}
    three_week_avgs[c] = {}
    four_week_avgs[c] = {}

    for t in tests:
        recent[c][t] = get_last(session, c, t)
        week_avgs[c][t] = get_avgs(session, c, t, 7)
        two_week_avgs[c][t] = get_avgs(session, c, t, 14)
        three_week_avgs[c][t] = get_avgs(session, c, t, 21)
        four_week_avgs[c][t] = get_avgs(session, c, t, 28)
        recent[c][t]['regression'] = False
        if (utils.check_regression(week_avgs[c][t], recent[c][t], 5) or
            utils.check_regression(two_week_avgs[c][t], recent[c][t], 5) or
            utils.check_regression(three_week_avgs[c][t], recent[c][t], 5) or
            utils.check_regression(four_week_avgs[c][t], recent[c][t], 5)):
            recent[c][t]['regression'] = True

env = Environment(loader=FileSystemLoader('src'))
index_template = env.get_template('index.jinja')
test_template = env.get_template('test.jinja')

for t in tests:
    f = open(f'www/{t}.html', 'w')
    print(f'Writing {t}.html')
    f.write(test_template.render(test=t, configs=configs,
                                 avgs=[week_avgs, two_week_avgs,
                                       three_week_avgs, four_week_avgs],
                                 recent=recent))
    f.close()

f = open(f'www/index.html', 'w')
print(f'Writing index.html')
f.write(index_template.render(tests=tests, configs=configs, recent=recent))
f.close()

locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
formatter = mdates.ConciseDateFormatter(locator)

for t in tests:
    last = get_last_test(session, t)
    for k,v in last.items():
        if not isinstance(v, numbers.Number):
            continue
        if "id" in k:
            continue
        if v == 0:
            continue

        print(f'Generating graph for {t}_{k}')
        # Start a new figure
        plt.figure()
        fig, ax = plt.subplots()

        # format the ticks
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

        datemin = None
        datemax = None
        for c in configs:
            results = get_all_results(session, c, t)
            (dates, values) = get_values_for_key(results, k)
            if dates is None:
                continue

            # figure out the range
            curmin = np.datetime64(dates[0], 'D')
            curmax = np.datetime64(dates[-1], 'D') + 1
            if not datemin or curmin < datemin:
                datemin = curmin
            if not datemax or curmax > datemax:
                datemax = curmax
            plt.plot(dates, values, label=c)

        ax.set_xlim(datemin, datemax)
        fig.autofmt_xdate()
        plt.title(f"{t} results over time")
        plt.legend(bbox_to_anchor=(1.04, 1), borderaxespad=0)
        plt.savefig(f"www/{t}_{k}.png", bbox_inches="tight")
        plt.close('all')
