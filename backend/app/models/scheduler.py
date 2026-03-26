"""
ABOUTME: Scheduler task execution log model.
ABOUTME: Tracks scheduled report generation and notification history.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date
from app.core.database import Base


class SchedulerLog(Base):
    """
    Log entries for scheduled tasks execution.
    Records when tasks run, their status, and any errors.
    """
    __tablename__ = "scheduler_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), nullable=False, index=True)  # e.g., 'morning_report', 'evening_report'
    user_id = Column(Integer, nullable=True, index=True)  # NULL for system-wide tasks

    # Execution details
    status = Column(String(20), nullable=False)  # 'started', 'completed', 'failed'
    started_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Execution duration in milliseconds

    # Results
    message = Column(Text, nullable=True)  # Success message or error description
    details = Column(Text, nullable=True)  # JSON details for debugging

    __table_args__ = (
        Index('ix_scheduler_logs_task_started', 'task_name', 'started_at'),
    )

    def __repr__(self):
        return f"<SchedulerLog(task={self.task_name}, status={self.status}, at={self.started_at})>"


class ReportRetryLog(Base):
    """
    Report generation retry log.
    Tracks retry attempts when Garmin data is stale (>2h old).
    """
    __tablename__ = "report_retry_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    report_type = Column(String(20), nullable=False)  # 'morning' / 'evening'
    report_date = Column(Date, nullable=False, index=True)
    
    # Retry tracking
    retry_count = Column(Integer, default=0, nullable=False)  # Current retry count (0-indexed)
    max_retries = Column(Integer, default=3, nullable=False)  # Maximum allowed retries
    
    # Timing
    next_retry_at = Column(DateTime, nullable=True)  # Next retry time (UTC)
    last_retry_at = Column(DateTime, nullable=True)  # Last retry attempt time (UTC)
    
    # Status tracking
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'completed', 'failed', 'expired'
    last_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    # user = relationship("User", back_populates="retry_logs")
    
    __table_args__ = (
        Index('ix_report_retry_logs_user_date', 'user_id', 'report_date'),
        Index('ix_report_retry_logs_next_retry', 'next_retry_at', 'status'),
    )

    def __repr__(self):
        return f"<ReportRetryLog(user={self.user_id}, type={self.report_type}, date={self.report_date}, retry={self.retry_count}/{self.max_retries})>"
