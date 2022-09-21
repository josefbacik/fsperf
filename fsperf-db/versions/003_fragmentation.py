from sqlalchemy import *
from migrate import *

meta = MetaData()

frag_table = Table(
    "fragmentation", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('bg_count', Integer, default=0),
    Column('fragmented_bg_count', Integer, default=0),
    Column('frag_pct_mean', Float, default=0.0),
    Column('frag_pct_min', Float, default=0.0),
    Column('frag_pct_p50', Float, default=0.0),
    Column('frag_pct_p95', Float, default=0.0),
    Column('frag_pct_p99', Float, default=0.0),
    Column('frag_pct_max', Float, default=0.0),
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    run_table = Table("runs", meta, autoload=True)
    frag_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    frag_table.drop()
