import datetime
import socket
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
    hostname = Column(String, default=socket.gethostname())
    purpose = Column(String, default="continuous")
    time = Column(DateTime, default=datetime.datetime.utcnow)

    time_results = relationship("TimeResult", backref="runs",
                                order_by="TimeResult.id",
                                cascade="all,delete")
    fio_results = relationship("FioResult", backref="runs",
                               order_by="FioResult.id",
                               cascade="all,delete")
    dbench_results = relationship("DbenchResult", backref="runs",
                                  order_by="DbenchResult.id",
                                  cascade="all,delete")

class FioResult(Base):
    __tablename__ = 'fio_results'

    id = Column(Integer, primary_key=True)
    run_id = Column(ForeignKey('runs.id', ondelete="CASCADE"))
    read_io_bytes = Column(Integer, default=0)
    elapsed = Column(Integer, default=0)
    sys_cpu = Column(Float, default=0.0)
    read_lat_ns_min = Column(Integer, default=0)
    read_lat_ns_max = Column(Integer, default=0)
    read_lat_ns_mean = Column(Integer, default=0)
    read_clat_ns_p50 = Column(Integer, default=0)
    read_clat_ns_p99 = Column(Integer, default=0)
    read_clat_ns_mean = Column(Integer, default=0)
    read_iops = Column(Float, default=0)
    read_io_kbytes = Column(Integer, default=0)
    read_bw_bytes = Column(Integer, default=0)
    write_lat_ns_min = Column(Integer, default=0)
    write_lat_ns_max = Column(Integer, default=0)
    write_lat_ns_mean = Column(Integer, default=0)
    write_clat_ns_p50 = Column(Integer, default=0)
    write_clat_ns_p99 = Column(Integer, default=0)
    write_clat_ns_mean = Column(Integer, default=0)
    write_iops = Column(Float, default=0.0)
    write_io_kbytes = Column(Integer, default=0)
    write_bw_bytes = Column(Integer, default=0)

    def load_from_dict(self, inval):
        for k in dir(self):
            if k not in inval:
                continue
            setattr(self, k, inval[k])

class TimeResult(Base):
    __tablename__ = 'time_results'
    id = Column(Integer, primary_key=True)
    run_id = Column(ForeignKey('runs.id', ondelete="CASCADE"))
    elapsed = Column(Float, default=0.0)

class DbenchResult(Base):
    __tablename__ = 'dbench_results'
    id = Column(Integer, primary_key=True)
    run_id = Column(ForeignKey('runs.id', ondelete="CASCADE"))
    throughput = Column(Float, default=0.0)
    ntcreatex = Column(Float, default=0.0)
    close = Column(Float, default=0.0)
    rename = Column(Float, default=0.0)
    unlink = Column(Float, default=0.0)
    deltree = Column(Float, default=0.0)
    mkdir = Column(Float, default=0.0)
    qpathinfo = Column(Float, default=0.0)
    qfileinfo = Column(Float, default=0.0)
    qfsinfo = Column(Float, default=0.0)
    sfileinfo = Column(Float, default=0.0)
    find = Column(Float, default=0.0)
    writex = Column(Float, default=0.0)
    readx = Column(Float, default=0.0)
    lockx = Column(Float, default=0.0)
    unlockx = Column(Float, default=0.0)
    flush = Column(Float, default=0.0)

    def load_from_dict(self, inval):
        for k in dir(self):
            if k not in inval:
                continue
            setattr(self, k, inval[k])
