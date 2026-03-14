# ABOUTME: Scheduler logs API endpoints for viewing task execution history
# ABOUTME: Provides list and detail endpoints for scheduler log entries
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, SchedulerLog
from app.schemas import SchedulerLogResponse, SchedulerLogListResponse

router = APIRouter(prefix="/scheduler-logs", tags=["Scheduler Logs"])


@router.get("", response_model=SchedulerLogListResponse)
async def list_scheduler_logs(
    task_name: Optional[str] = Query(None, description="Filter by task name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List scheduler task execution logs.

    Supports filtering by task name and status.
    Results are ordered by started_at descending (newest first).
    """
    query = db.query(SchedulerLog)

    if task_name:
        query = query.filter(SchedulerLog.task_name == task_name)

    if status:
        query = query.filter(SchedulerLog.status == status)

    total = query.count()
    logs = query.order_by(SchedulerLog.started_at.desc()).offset(offset).limit(limit).all()

    return SchedulerLogListResponse(logs=logs, count=total)


@router.get("/{log_id}", response_model=SchedulerLogResponse)
async def get_scheduler_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific scheduler log entry by ID.

    Returns detailed information about a task execution.
    """
    log = db.query(SchedulerLog).filter(SchedulerLog.id == log_id).first()

    if not log:
        raise HTTPException(status_code=404, detail="Scheduler log not found")

    return log
