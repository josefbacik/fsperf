from sqlalchemy import *
from migrate import *

meta = MetaData()

btrfs_commit_stats_trace_table = Table(
    "btrfs_commit_stats", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('commits', Integer, default=0),
    Column('avg_commit_ms', Float, default=0.0),
    Column('max_commit_ms', Integer, default=0),
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    run_table = Table("runs", meta, autoload=True)
    btrfs_commit_stats_trace_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    btrfs_commit_stats_trace_table.drop()
