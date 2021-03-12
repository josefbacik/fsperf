from ResultData import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jinja2 import Template,Environment,FileSystemLoader
import datetime
import utils

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
        order_by(Run.id.desc()).first()
    results = utils.results_to_dict(result)
    ret = {}
    for k,v in results.items():
        ret[k] = {'value': v}
    return ret

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
    f.write(test_template.render(test=t, configs=configs,
                                 avgs=[week_avgs, two_week_avgs,
                                       three_week_avgs, four_week_avgs],
                                 recent=recent))
    f.close()

f = open(f'www/index.html', 'w')
f.write(index_template.render(tests=tests, configs=configs, recent=recent))
f.close()
