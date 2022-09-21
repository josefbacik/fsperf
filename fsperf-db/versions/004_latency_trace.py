from sqlalchemy import *
from migrate import *

meta = MetaData()

latency_trace_table = Table(
    "latency_traces", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('function', String),
    Column('ns_mean', Float, default=0.0),
    Column('ns_min', Float, default=0.0),
    Column('ns_p50', Float, default=0.0),
    Column('ns_p95', Float, default=0.0),
    Column('ns_p99', Float, default=0.0),
    Column('ns_max', Float, default=0.0),
    Column('calls', Integer, default=0),
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    run_table = Table("runs", meta, autoload=True)
    latency_trace_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    latency_trace_table.drop()
