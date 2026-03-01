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

    Note: Garmin sleep timeseries data is only available after the sleep
    period completes. For dates >= today, we return the most recent
    available data (typically yesterday's sleep data).
    """
    # Use current user if no user_id specified
    query_user_id = user_id if user_id is not None else current_user.id

    query_date = target_date
    local_tz_offset = datetime.now().astimezone().utcoffset() or timedelta(0)

    # Helper function to query records for a specific date
    def query_records_for_date(search_date: date):
        local_start = datetime.combine(search_date, datetime.min.time())
        local_end = datetime.combine(search_date + timedelta(days=1), datetime.min.time())
        start_datetime = local_start - local_tz_offset
        end_datetime = local_end - local_tz_offset
        return db.query(BodyStatusTimeseries).filter(
            BodyStatusTimeseries.user_id == query_user_id,
            BodyStatusTimeseries.timestamp >= start_datetime,
            BodyStatusTimeseries.timestamp < end_datetime
        ).order_by(BodyStatusTimeseries.timestamp).all()

    # First, try to get data for the requested date
    records = query_records_for_date(target_date)

    # If no data found, fall back to the most recent available data
    if not records:
        latest_record = db.query(BodyStatusTimeseries).filter(
            BodyStatusTimeseries.user_id == query_user_id
        ).order_by(BodyStatusTimeseries.timestamp.desc()).first()

        if latest_record:
            # Convert UTC timestamp to local date
            local_timestamp = latest_record.timestamp + local_tz_offset
            query_date = local_timestamp.date()
            records = query_records_for_date(query_date)
        else:
            # No data at all for this user
            return BodyStatusTimeseriesResponse(
                user_id=query_user_id,
                date=target_date,
                requested_date=target_date,
                data=[]
            )

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
        date=query_date,
        requested_date=target_date if target_date != query_date else None,
        data=data_points
    )
