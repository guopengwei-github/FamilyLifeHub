"""
ABOUTME: Scheduler task execution log model.
ABOUTME: Tracks scheduled report generation and notification history.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from datetime import datetime, timezone
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
