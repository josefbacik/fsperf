from sqlalchemy import *
from migrate import *

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    fio_result_table = Table("fio_results", meta, autoload=True)
    read_lat_mean_col = Column('read_lat_ns_mean', Integer, default=0)
    read_clat_mean_col = Column('read_clat_ns_mean', Integer, default=0)
    write_lat_mean_col = Column('write_lat_ns_mean', Integer, default=0)
    write_clat_mean_col = Column('write_clat_ns_mean', Integer, default=0)
    read_lat_mean_col.create(fio_result_table)
    read_clat_mean_col.create(fio_result_table)
    write_lat_mean_col.create(fio_result_table)
    write_clat_mean_col.create(fio_result_table)

def downgrade(migrate_engine):
    meta.bind = migrate_engine
    fio_result_table = Table("fio_results", meta, autoload=True)
    fio_result_table.c.read_lat_ns_mean.drop()
    fio_result_table.c.read_clat_ns_mean.drop()
    fio_result_table.c.write_lat_ns_mean.drop()
    fio_result_table.c.write_clat_ns_mean.drop()
