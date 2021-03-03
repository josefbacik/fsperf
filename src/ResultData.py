import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Table, Column, Integer, String, ForeignKey, DateTime,
                        Float)
from sqlalchemy.orm import relationship

Base = declarative_base()

class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    kernel = Column(String)
    config = Column(String)
    name = Column(String)
    time = Column(DateTime, default=datetime.datetime.utcnow)

    time_results = relationship("TimeResult", backref="runs",
                                order_by="TimeResult.id")
    fio_results = relationship("FioResult", backref="runs",
                               order_by="FioResult.id")

class FioResult(Base):
    __tablename__ = 'fio_results'

    id = Column(Integer, primary_key=True)
    run_id = Column(ForeignKey('runs.id'))
    read_io_bytes = Column(Integer, default=0)
    elapsed = Column(Integer, default=0)
    sys_cpu = Column(Float, default=0.0)
    read_lat_ns_min = Column(Integer, default=0)
    read_lat_ns_max = Column(Integer, default=0)
    read_clat_ns_p50 = Column(Integer, default=0)
    read_clat_ns_p99 = Column(Integer, default=0)
    read_iops = Column(Float, default=0)
    read_io_kbytes = Column(Integer, default=0)
    read_bw_bytes = Column(Integer, default=0)
    write_lat_ns_min = Column(Integer, default=0)
    write_lat_ns_max = Column(Integer, default=0)
    write_iops = Column(Float, default=0.0)
    write_io_kbytes = Column(Integer, default=0)
    write_bw_bytes = Column(Integer, default=0)
    write_clat_ns_p50 = Column(Integer, default=0)
    write_clat_ns_p99 = Column(Integer, default=0)

    def load_from_dict(self, inval):
        for k in dir(self):
            if k not in inval:
                continue
            setattr(self, k, inval[k])

class TimeResult(Base):
    __tablename__ = 'time_results'
    id = Column(Integer, primary_key=True)
    run_id = Column(ForeignKey('runs.id'))
    elapsed = Column(Float, default=0.0)
