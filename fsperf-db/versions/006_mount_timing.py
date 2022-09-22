from sqlalchemy import *
from migrate import *

meta = MetaData()

mount_timing_table = Table(
    "mount_timings", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('end_state_umount_ns', Integer, default=0),
    Column('end_state_mount_ns', Integer, default=0),
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    run_table = Table("runs", meta, autoload=True)
    mount_timing_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    mount_timing_table.drop()
