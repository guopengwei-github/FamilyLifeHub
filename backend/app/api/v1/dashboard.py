"""
API endpoints for dashboard data retrieval.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Annotated, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_user
from app.models import User
from app.schemas import TrendResponse, OverviewResponse, SummaryResponse
from app.services.dashboard import (
    get_daily_trends, get_today_overview, get_user_daily_trends,
    get_user_overview, get_user_summary
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Optional auth dependency that returns None if not authenticated
async def get_optional_current_user(
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    try:
        return await get_current_user(db=db)
    except Exception:
        return None


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    target_date: date = Query(default=None, description="Target date (defaults to today)"),
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Get overview metrics.

    - If authenticated and no user_id: returns current user's data only
    - If authenticated and user_id provided: returns data for that user (if it's the current user)
    - If not authenticated: returns all users' data (public view)

    Returns current day's sleep, exercise, work time, and focus score.
    """
    if target_date is None:
        target_date = date.today()

    # Determine whose data to return
    if current_user:
        # Authenticated user can only see their own data
        requested_user_id = user_id if user_id == current_user.id else current_user.id
        metrics = get_user_overview(db, requested_user_id, target_date)
    elif user_id:
        # Public view with specific user filter
        metrics = get_user_overview(db, user_id, target_date)
    else:
        # Public view - show all users
        metrics = get_today_overview(db, target_date)

    return OverviewResponse(
        date=target_date,
        metrics=metrics
    )


@router.get("/summary", response_model=SummaryResponse)
async def get_dashboard_summary(
    target_date: Optional[date] = Query(default=None, description="Target date (defaults to today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's summary metrics for dashboard header.

    Returns core daily metrics: sleep hours, steps, calories, work hours, and stress level.
    Requires authentication.
    """
    summary = get_user_summary(db, current_user.id, target_date)
    return summary


@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to retrieve"),
    end_date: date = Query(default=None, description="End date (defaults to today)"),
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Get daily trend data for visualization.

    - If authenticated and no user_id: returns current user's data only
    - If authenticated and user_id provided: returns data for that user (if it's the current user)
    - If not authenticated: returns all users' data (public view)

    Returns aggregated sleep vs work load data for the specified time range.
    Useful for identifying negative correlations between work and sleep.
    """
    if end_date is None:
        end_date = date.today()

    start_date = end_date - timedelta(days=days - 1)

    # Determine whose data to return
    if current_user:
        # Authenticated user can only see their own data
        requested_user_id = user_id if user_id == current_user.id else current_user.id
        trends = get_user_daily_trends(db, requested_user_id, start_date, end_date)
    elif user_id:
        # Public view with specific user filter
        trends = get_user_daily_trends(db, user_id, start_date, end_date)
    else:
        # Public view - show all users
        trends = get_daily_trends(db, start_date, end_date)

    return TrendResponse(
        start_date=start_date,
        end_date=end_date,
        data=trends
    )
