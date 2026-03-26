"""
Migration: Add report_retry_logs table

Creates table for tracking report generation retries when Garmin data is stale.
"""
from datetime import datetime, timezone
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Text, Date, ForeignKey, Index
from app.core.config import settings


def upgrade():
    """Create report_retry_logs table."""
    engine = create_engine(settings.database_url)
    metadata = MetaData()
    
    table = Table(
        'report_retry_logs',
        metadata,
        Column('id', Integer, primary_key=True, index=True),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False, index=True),
        Column('report_type', String(20), nullable=False),  # 'morning' / 'evening'
        Column('report_date', Date, nullable=False),
        Column('retry_count', Integer, default=0, nullable=False),
        Column('max_retries', Integer, default=3, nullable=False),
        Column('next_retry_at', DateTime, nullable=True),  # UTC
        Column('last_retry_at', DateTime, nullable=True),  # UTC
        Column('status', String(20), default='pending', nullable=False),
        Column('last_error', Text, nullable=True),
        Column('created_at', DateTime, default=lambda: datetime.now(timezone.utc), nullable=False),
        Column('updated_at', DateTime, default=lambda: datetime.now(timezone.utc), nullable=False),
        
        Index('ix_report_retry_logs_user_date', 'user_id', 'report_date'),
        Index('ix_report_retry_logs_next_retry', 'next_retry_at', 'status'),
    )
    
    metadata.create_all(engine)
    print("✓ Created report_retry_logs table")


def downgrade():
    """Drop report_retry_logs table."""
    engine = create_engine(settings.database_url)
    metadata = MetaData()
    
    table = Table('report_retry_logs', metadata, autoload_with=engine)
    table.drop(engine)
    print("✓ Dropped report_retry_logs table")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
