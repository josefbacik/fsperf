from sqlalchemy import *
from migrate import *

meta = MetaData()

run_table = Table(
    "runs", meta,
    Column('id', Integer, primary_key=True),
    Column('kernel', String),
    Column('config', String),
    Column('name', String),
    Column('hostname', String),
    Column('purpose', String),
    Column('time', DateTime),
)

fio_result_table = Table(
    "fio_results", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('read_io_bytes', Integer, default=0),
    Column('elapsed', Integer, default=0),
    Column('sys_cpu', Float, default=0.0),
    Column('read_lat_ns_min', Integer, default=0),
    Column('read_lat_ns_max', Integer, default=0),
    Column('read_clat_ns_p50', Integer, default=0),
    Column('read_clat_ns_p99', Integer, default=0),
    Column('read_iops', Float, default=0),
    Column('read_io_kbytes', Integer, default=0),
    Column('read_bw_bytes', Integer, default=0),
    Column('write_lat_ns_min', Integer, default=0),
    Column('write_lat_ns_max', Integer, default=0),
    Column('write_iops', Float, default=0.0),
    Column('write_io_kbytes', Integer, default=0),
    Column('write_bw_bytes', Integer, default=0),
    Column('write_clat_ns_p50', Integer, default=0),
    Column('write_clat_ns_p99', Integer, default=0),
)

time_result_table = Table(
    "time_results", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('elapsed', Float, default=0.0),
)

dbench_result_table = Table(
    "dbench_results", meta,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('runs.id', ondelete="CASCADE")),
    Column('throughput', Float, default=0.0),
    Column('ntcreatex', Float, default=0.0),
    Column('close', Float, default=0.0),
    Column('rename', Float, default=0.0),
    Column('unlink', Float, default=0.0),
    Column('deltree', Float, default=0.0),
    Column('mkdir', Float, default=0.0),
    Column('qpathinfo', Float, default=0.0),
    Column('qfileinfo', Float, default=0.0),
    Column('qfsinfo', Float, default=0.0),
    Column('sfileinfo', Float, default=0.0),
    Column('find', Float, default=0.0),
    Column('writex', Float, default=0.0),
    Column('readx', Float, default=0.0),
    Column('lockx', Float, default=0.0),
    Column('unlockx', Float, default=0.0),
    Column('flush', Float, default=0.0),
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    run_table.create()
    fio_result_table.create()
    time_result_table.create()
    dbench_result_table.create()

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    run_table.drop()
    fio_result_table.drop()
    time_result_table.drop()
    dbench_result_table.drop()
