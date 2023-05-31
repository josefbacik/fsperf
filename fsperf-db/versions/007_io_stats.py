from sqlalchemy import *
from migrate import *

meta = MetaData()

dev_iostats_table = Table(
    "io_stats", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('dev_read_iops', Integer, default=0),
    Column('dev_read_kbytes', Integer, default=0),
    Column('dev_write_iops', Integer, default=0),
    Column('dev_write_kbytes', Integer, default=0)
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    run_table = Table("runs", meta, autoload=True)
    dev_iostats_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    dev_iostats_table.drop()
