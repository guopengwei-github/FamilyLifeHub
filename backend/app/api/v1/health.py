"""
API endpoints for health metric CRUD operations.
Allows authenticated users to manage their own health data.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, HealthMetric
from app.schemas import HealthMetricResponse, HealthMetricBase

router = APIRouter(prefix="/health/metrics", tags=["Health"])


@router.get("", response_model=List[HealthMetricResponse])
async def list_health_metrics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List the current user's health metrics.

    Optional date range filtering via query parameters.
    """
    query = db.query(HealthMetric).filter(HealthMetric.user_id == current_user.id)

    if start_date:
        query = query.filter(HealthMetric.date >= start_date)
    if end_date:
        query = query.filter(HealthMetric.date <= end_date)

    # Order by date descending (most recent first)
    metrics = query.order_by(HealthMetric.date.desc()).all()
    return metrics


@router.get("/{metric_date}", response_model=HealthMetricResponse)
async def get_health_metric(
    metric_date: date,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific health metric by date.

    Only returns metrics belonging to the authenticated user.
    """
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == current_user.id,
        HealthMetric.date == metric_date
    ).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health metric found for date {metric_date}"
        )

    return metric


@router.post("", response_model=HealthMetricResponse, status_code=status.HTTP_201_CREATED)
async def create_health_metric(
    metric_data: HealthMetricBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new health metric.

    If a metric already exists for the user on the same date, it will be updated (upsert).
    """
    # Check if metric already exists for this date
    existing = db.query(HealthMetric).filter(
        HealthMetric.user_id == current_user.id,
        HealthMetric.date == metric_data.date
    ).first()

    if existing:
        # Update existing metric
        for key, value in metric_data.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Create new metric
    new_metric = HealthMetric(
        user_id=current_user.id,
        **metric_data.model_dump()
    )
    db.add(new_metric)
    db.commit()
    db.refresh(new_metric)

    return new_metric


@router.put("/{metric_date}", response_model=HealthMetricResponse)
async def update_health_metric(
    metric_date: date,
    metric_data: HealthMetricBase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing health metric.

    Only allows updating metrics belonging to the authenticated user.
    """
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == current_user.id,
        HealthMetric.date == metric_date
    ).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health metric found for date {metric_date}"
        )

    # Update fields
    for key, value in metric_data.model_dump(exclude_unset=True).items():
        setattr(metric, key, value)

    metric.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(metric)

    return metric


@router.delete("/{metric_date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_metric(
    metric_date: date,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a health metric.

    Only allows deleting metrics belonging to the authenticated user.
    """
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == current_user.id,
        HealthMetric.date == metric_date
    ).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health metric found for date {metric_date}"
        )

    db.delete(metric)
    db.commit()

    return None
