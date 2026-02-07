"""
API endpoints for data ingestion (health and work metrics).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_api_key
from app.models import HealthMetric, WorkMetric, User
from app.schemas import (
    HealthMetricCreate,
    HealthMetricResponse,
    WorkMetricCreate,
    WorkMetricResponse
)

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])


@router.post("/health", response_model=HealthMetricResponse, status_code=status.HTTP_201_CREATED)
async def ingest_health_data(
    data: HealthMetricCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest health metrics data (from Garmin or manual input).

    Requires X-API-Key header for authentication.
    If a record for the same user and date exists, it will be updated.
    """
    # Verify user exists
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {data.user_id} not found"
        )

    # Check if record already exists for this user and date
    existing = db.query(HealthMetric).filter(
        HealthMetric.user_id == data.user_id,
        HealthMetric.date == data.date
    ).first()

    if existing:
        # Update existing record
        for key, value in data.model_dump(exclude={'user_id', 'date'}).items():
            if value is not None:  # Only update non-null values
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new record
        health_metric = HealthMetric(**data.model_dump())
        db.add(health_metric)
        db.commit()
        db.refresh(health_metric)
        return health_metric


@router.post("/work", response_model=WorkMetricResponse, status_code=status.HTTP_201_CREATED)
async def ingest_work_data(
    data: WorkMetricCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest work metrics data (from desktop client heartbeat).

    Requires X-API-Key header for authentication.
    Creates a new record for each heartbeat packet.
    """
    # Verify user exists
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {data.user_id} not found"
        )

    # Create new work metric record
    work_metric = WorkMetric(**data.model_dump())
    db.add(work_metric)
    db.commit()
    db.refresh(work_metric)
    return work_metric
