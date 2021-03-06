from sqlalchemy import *
from migrate import *
import socket

def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    runs = Table('runs', meta, autoload=True)
    hostnamec = Column('hostname', String, default=socket.gethostname())
    purposec = Column('purpose', String, default="continuous")
    hostnamec.create(runs)
    purposec.create(runs)


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    runs = Table('runs', meta, autoload=True)
    runs.c.hostname.drop()
    runs.c.purpose.drop()
