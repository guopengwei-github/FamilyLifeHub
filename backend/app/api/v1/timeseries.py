# ABOUTME: API endpoints for time-series body status data
# ABOUTME: Provides minute-level body battery, stress, and heart rate readings
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, BodyStatusTimeseries
from app.schemas import BodyStatusTimeseriesResponse, BodyStatusTimeseriesPoint

router = APIRouter(prefix="/timeseries", tags=["timeseries"])


@router.get("/body-status", response_model=BodyStatusTimeseriesResponse)
async def get_body_status_timeseries(
    user_id: Optional[int] = Query(None, description="User ID (defaults to current user)"),
    target_date: date = Query(..., description="Date to fetch data for (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get body status timeseries data for a specific date.
    Returns minute-level body battery, stress, and heart rate readings.
    """
    # Use current user if no user_id specified
    query_user_id = user_id if user_id is not None else current_user.id

    # Calculate date range (start of day to end of day in UTC)
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    # Query timeseries data
    records = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == query_user_id,
        BodyStatusTimeseries.timestamp >= start_datetime,
        BodyStatusTimeseries.timestamp < end_datetime
    ).order_by(BodyStatusTimeseries.timestamp).all()

    # Convert to response format
    data_points = [
        BodyStatusTimeseriesPoint(
            timestamp=record.timestamp,
            body_battery=record.body_battery,
            stress_level=record.stress_level,
            heart_rate=record.heart_rate
        )
        for record in records
    ]

    return BodyStatusTimeseriesResponse(
        user_id=query_user_id,
        date=target_date,
        data=data_points
    )
