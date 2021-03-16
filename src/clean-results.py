from ResultData import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("labels", nargs='+', type=str,
                    help="Labels to delete the results for")
args = parser.parse_args()

engine = create_engine('sqlite:///fsperf-results.db')
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

for p in args.labels:
    results = session.query(Run).\
            outerjoin(FioResult).\
            outerjoin(DbenchResult).\
            outerjoin(TimeResult).\
            filter(Run.purpose == p).all()
    for r in results:
        session.delete(r)
    session.commit()
