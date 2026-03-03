"""
API endpoints for health reports.

Provides endpoints to retrieve and regenerate morning/evening health reports.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, HealthReport
from app.schemas import (
    HealthReportResponse,
    HealthReportListResponse,
    HealthReportRegenerateRequest,
    UserProfileUpdate,
    UserProfileResponse
)
from app.services.llm.zhipu import ZhipuProvider
from app.services.report_generator import generate_morning_report, generate_evening_report
from app.core.config import settings

router = APIRouter(prefix="/reports", tags=["Health Reports"])


def _calculate_age(birth_date: date | None) -> int | None:
    """Calculate age from birth date."""
    if birth_date is None:
        return None
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def get_llm_provider() -> ZhipuProvider:
    """Get configured LLM provider."""
    return ZhipuProvider(
        api_key=settings.zhipu_api_key,
        model=settings.zhipu_model,
        base_url=settings.zhipu_base_url
    )


@router.get("/morning", response_model=HealthReportResponse)
async def get_morning_report(
    report_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get morning readiness report for a specific date.

    Defaults to today if no date specified.
    """
    target_date = report_date or date.today()

    report = db.query(HealthReport).filter(
        HealthReport.user_id == current_user.id,
        HealthReport.report_date == target_date,
        HealthReport.report_type == 'morning'
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Morning report not found for {target_date}"
        )

    return report


@router.get("/evening", response_model=HealthReportResponse)
async def get_evening_report(
    report_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get evening review report for a specific date.

    Defaults to today if no date specified.
    """
    target_date = report_date or date.today()

    report = db.query(HealthReport).filter(
        HealthReport.user_id == current_user.id,
        HealthReport.report_date == target_date,
        HealthReport.report_type == 'evening'
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evening report not found for {target_date}"
        )

    return report


@router.get("/history", response_model=HealthReportListResponse)
async def get_report_history(
    report_type: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical health reports.

    Args:
        report_type: Filter by 'morning' or 'evening' (optional)
        limit: Maximum number of reports to return (default 10)
    """
    query = db.query(HealthReport).filter(
        HealthReport.user_id == current_user.id
    )

    if report_type:
        query = query.filter(HealthReport.report_type == report_type)

    reports = query.order_by(
        HealthReport.report_date.desc(),
        HealthReport.generated_at.desc()
    ).limit(limit).all()

    return HealthReportListResponse(
        reports=reports,
        count=len(reports)
    )


@router.post("/regenerate", response_model=HealthReportResponse, status_code=status.HTTP_201_CREATED)
async def regenerate_report(
    request: HealthReportRegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually regenerate a health report.

    This will delete the existing report and generate a new one.
    """
    target_date = request.report_date or date.today()

    if request.report_type not in ('morning', 'evening'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_type must be 'morning' or 'evening'"
        )

    # Delete existing report if any
    db.query(HealthReport).filter(
        HealthReport.user_id == current_user.id,
        HealthReport.report_date == target_date,
        HealthReport.report_type == request.report_type
    ).delete()

    # Generate new report
    llm_provider = get_llm_provider()

    try:
        if request.report_type == 'morning':
            report_data = await generate_morning_report(
                db=db,
                user_id=current_user.id,
                report_date=target_date,
                llm_provider=llm_provider
            )
        else:
            report_data = await generate_evening_report(
                db=db,
                user_id=current_user.id,
                report_date=target_date,
                llm_provider=llm_provider
            )

        # Save to database
        report = HealthReport(
            user_id=report_data['user_id'],
            report_date=report_data['report_date'],
            report_type=report_data['report_type'],
            content=report_data['content'],
            input_context=report_data['input_context'],
            llm_model=report_data['llm_model']
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        return report

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


# User profile endpoints for report personalization

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user profile for health report personalization."""
    return UserProfileResponse(
        birth_date=current_user.birth_date,
        gender=current_user.gender,
        weight_kg=current_user.weight_kg,
        height_cm=current_user.height_cm,
        age=_calculate_age(current_user.birth_date)
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile for health report personalization."""
    if profile.birth_date is not None:
        current_user.birth_date = profile.birth_date
    if profile.gender is not None:
        if profile.gender not in ('male', 'female', 'other'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="gender must be 'male', 'female', or 'other'"
            )
        current_user.gender = profile.gender
    if profile.weight_kg is not None:
        current_user.weight_kg = profile.weight_kg
    if profile.height_cm is not None:
        current_user.height_cm = profile.height_cm

    db.commit()
    db.refresh(current_user)

    return UserProfileResponse(
        birth_date=current_user.birth_date,
        gender=current_user.gender,
        weight_kg=current_user.weight_kg,
        height_cm=current_user.height_cm,
        age=_calculate_age(current_user.birth_date)
    )
