"""initial create

Revision ID: f2b6313d4618
Revises:
Create Date: 2024-10-04 16:05:59.876022

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String


# revision identifiers, used by Alembic.
revision: str = 'f2b6313d4618'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runs",
        Column('id', Integer, primary_key=True),
        Column('kernel', String),
        Column('config', String),
        Column('name', String),
        Column('hostname', String),
        Column('purpose', String),
        Column('time', DateTime),
    )

    op.create_table(
        "fio_results",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
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
        Column('read_lat_ns_mean', Integer, default=0),
        Column('read_clat_ns_mean', Integer, default=0),
        Column('write_lat_ns_mean', Integer, default=0),
        Column('write_clat_ns_mean', Integer, default=0),
    )

    op.create_table(
        "time_results",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        Column('elapsed', Float, default=0.0),
    )

    op.create_table(
        "dbench_results",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
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

    op.create_table(
        "fragmentation",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        Column('bg_count', Integer, default=0),
        Column('fragmented_bg_count', Integer, default=0),
        Column('frag_pct_mean', Float, default=0.0),
        Column('frag_pct_min', Float, default=0.0),
        Column('frag_pct_p50', Float, default=0.0),
        Column('frag_pct_p95', Float, default=0.0),
        Column('frag_pct_p99', Float, default=0.0),
        Column('frag_pct_max', Float, default=0.0),
    )

    op.create_table(
        "latency_traces",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        Column('function', String),
        Column('ns_mean', Float, default=0.0),
        Column('ns_min', Float, default=0.0),
        Column('ns_p50', Float, default=0.0),
        Column('ns_p95', Float, default=0.0),
        Column('ns_p99', Float, default=0.0),
        Column('ns_max', Float, default=0.0),
        Column('calls', Integer, default=0),
    )

    op.create_table(
        "btrfs_commit_stats",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        Column('commits', Integer, default=0),
        Column('avg_commit_ms', Float, default=0.0),
        Column('max_commit_ms', Integer, default=0),
    )

    op.create_table(
        "mount_timings",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        Column('end_state_umount_ns', Integer, default=0),
        Column('end_state_mount_ns', Integer, default=0),
    )

    op.create_table(
        "io_stats",
        Column('id', Integer, primary_key=True),
        Column('run_id', Integer, ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        Column('dev_read_iops', Integer, default=0),
        Column('dev_read_kbytes', Integer, default=0),
        Column('dev_write_iops', Integer, default=0),
        Column('dev_write_kbytes', Integer, default=0),
    )
    pass


def downgrade() -> None:
    pass
