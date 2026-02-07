"""
Service layer for dashboard data aggregation and calculations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from typing import List, Optional
from app.models import User, HealthMetric, WorkMetric, UserPreference
from app.schemas import (
    DailyTrendData, OverviewMetric, UserPreferenceResponse, UserPreferenceUpdate,
    SummaryResponse, SummaryMetric
)


def get_user_daily_trends(
    db: Session,
    user_id: int,
    start_date: date,
    end_date: date
) -> List[DailyTrendData]:
    """
    Calculate daily aggregated trends for a specific user within date range.

    Args:
        db: Database session
        user_id: User ID to filter by
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        List of DailyTrendData objects
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    trends = []
    current_date = start_date

    while current_date <= end_date:
        # Get health metrics for this user and date
        health = db.query(HealthMetric).filter(
            HealthMetric.user_id == user_id,
            HealthMetric.date == current_date
        ).first()

        # Aggregate work metrics for this user and date
        work_agg = db.query(
            func.sum(WorkMetric.screen_time_minutes).label('total_work_minutes'),
            func.avg(WorkMetric.focus_score).label('avg_focus_score')
        ).filter(
            WorkMetric.user_id == user_id,
            func.date(WorkMetric.timestamp) == current_date
        ).first()

        # Create trend data point
        trend = DailyTrendData(
            date=current_date,
            user_id=user.id,
            user_name=user.name,
            sleep_hours=health.sleep_hours if health else None,
            light_sleep_hours=health.light_sleep_hours if health else None,
            deep_sleep_hours=health.deep_sleep_hours if health else None,
            rem_sleep_hours=health.rem_sleep_hours if health else None,
            exercise_minutes=health.exercise_minutes if health else None,
            stress_level=health.stress_level if health else None,
            total_work_minutes=work_agg.total_work_minutes if work_agg.total_work_minutes else None,
            avg_focus_score=round(work_agg.avg_focus_score, 1) if work_agg.avg_focus_score else None,
            # Garmin advanced metrics
            steps=health.steps if health else None,
            calories=health.calories if health else None,
            distance_km=health.distance_km if health else None,
            body_battery=health.body_battery if health else None,
            spo2=health.spo2 if health else None,
            respiration_rate=health.respiration_rate if health else None,
            resting_hr=health.resting_hr if health else None,
            sleep_score=health.sleep_score if health else None
        )
        trends.append(trend)

        current_date += timedelta(days=1)

    return trends


def get_user_overview(db: Session, user_id: int, target_date: date = None) -> List[OverviewMetric]:
    """
    Get overview metrics for a specific user.

    Args:
        db: Database session
        user_id: User ID to filter by
        target_date: Target date (defaults to today)

    Returns:
        List of OverviewMetric objects (will contain at most one item)
    """
    if target_date is None:
        target_date = date.today()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    overview = []

    # Get health metrics
    health = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == target_date
    ).first()

    # Aggregate work metrics
    work_agg = db.query(
        func.sum(WorkMetric.screen_time_minutes).label('total_work_minutes'),
        func.avg(WorkMetric.focus_score).label('avg_focus_score')
    ).filter(
        WorkMetric.user_id == user_id,
        func.date(WorkMetric.timestamp) == target_date
    ).first()

    metric = OverviewMetric(
        user_id=user.id,
        user_name=user.name,
        sleep_hours=health.sleep_hours if health else None,
        light_sleep_hours=health.light_sleep_hours if health else None,
        deep_sleep_hours=health.deep_sleep_hours if health else None,
        rem_sleep_hours=health.rem_sleep_hours if health else None,
        exercise_minutes=health.exercise_minutes if health else None,
        stress_level=health.stress_level if health else None,
        total_work_minutes=work_agg.total_work_minutes if work_agg.total_work_minutes else None,
        avg_focus_score=round(work_agg.avg_focus_score, 1) if work_agg.avg_focus_score else None,
        # Garmin advanced metrics
        steps=health.steps if health else None,
        calories=health.calories if health else None,
        distance_km=health.distance_km if health else None,
        body_battery=health.body_battery if health else None,
        spo2=health.spo2 if health else None,
        respiration_rate=health.respiration_rate if health else None,
        resting_hr=health.resting_hr if health else None,
        sleep_score=health.sleep_score if health else None
    )
    overview.append(metric)

    return overview


def get_daily_trends(
    db: Session,
    start_date: date,
    end_date: date
) -> List[DailyTrendData]:
    """
    Calculate daily aggregated trends for all users within date range.

    Args:
        db: Database session
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        List of DailyTrendData objects
    """
    trends = []

    # Get all users
    users = db.query(User).all()

    # Iterate through each date in range
    current_date = start_date
    while current_date <= end_date:
        for user in users:
            # Get health metrics for this user and date
            health = db.query(HealthMetric).filter(
                HealthMetric.user_id == user.id,
                HealthMetric.date == current_date
            ).first()

            # Aggregate work metrics for this user and date
            # Calculate total work minutes and average focus score
            work_agg = db.query(
                func.sum(WorkMetric.screen_time_minutes).label('total_work_minutes'),
                func.avg(WorkMetric.focus_score).label('avg_focus_score')
            ).filter(
                WorkMetric.user_id == user.id,
                func.date(WorkMetric.timestamp) == current_date
            ).first()

            # Create trend data point
            trend = DailyTrendData(
                date=current_date,
                user_id=user.id,
                user_name=user.name,
                sleep_hours=health.sleep_hours if health else None,
                light_sleep_hours=health.light_sleep_hours if health else None,
                deep_sleep_hours=health.deep_sleep_hours if health else None,
                rem_sleep_hours=health.rem_sleep_hours if health else None,
                exercise_minutes=health.exercise_minutes if health else None,
                stress_level=health.stress_level if health else None,
                total_work_minutes=work_agg.total_work_minutes if work_agg.total_work_minutes else None,
                avg_focus_score=round(work_agg.avg_focus_score, 1) if work_agg.avg_focus_score else None,
                # Garmin advanced metrics
                steps=health.steps if health else None,
                calories=health.calories if health else None,
                distance_km=health.distance_km if health else None,
                body_battery=health.body_battery if health else None,
                spo2=health.spo2 if health else None,
                respiration_rate=health.respiration_rate if health else None,
                resting_hr=health.resting_hr if health else None,
                sleep_score=health.sleep_score if health else None
            )
            trends.append(trend)

        current_date += timedelta(days=1)

    return trends


def get_today_overview(db: Session, target_date: date = None) -> List[OverviewMetric]:
    """
    Get today's overview metrics for all users.

    Args:
        db: Database session
        target_date: Target date (defaults to today)

    Returns:
        List of OverviewMetric objects
    """
    if target_date is None:
        target_date = date.today()

    overview = []
    users = db.query(User).all()

    for user in users:
        # Get health metrics
        health = db.query(HealthMetric).filter(
            HealthMetric.user_id == user.id,
            HealthMetric.date == target_date
        ).first()

        # Aggregate work metrics
        work_agg = db.query(
            func.sum(WorkMetric.screen_time_minutes).label('total_work_minutes'),
            func.avg(WorkMetric.focus_score).label('avg_focus_score')
        ).filter(
            WorkMetric.user_id == user.id,
            func.date(WorkMetric.timestamp) == target_date
        ).first()

        metric = OverviewMetric(
            user_id=user.id,
            user_name=user.name,
            sleep_hours=health.sleep_hours if health else None,
            light_sleep_hours=health.light_sleep_hours if health else None,
            deep_sleep_hours=health.deep_sleep_hours if health else None,
            rem_sleep_hours=health.rem_sleep_hours if health else None,
            exercise_minutes=health.exercise_minutes if health else None,
            stress_level=health.stress_level if health else None,
            total_work_minutes=work_agg.total_work_minutes if work_agg.total_work_minutes else None,
            avg_focus_score=round(work_agg.avg_focus_score, 1) if work_agg.avg_focus_score else None,
            # Garmin advanced metrics
            steps=health.steps if health else None,
            calories=health.calories if health else None,
            distance_km=health.distance_km if health else None,
            body_battery=health.body_battery if health else None,
            spo2=health.spo2 if health else None,
            respiration_rate=health.respiration_rate if health else None,
            resting_hr=health.resting_hr if health else None,
            sleep_score=health.sleep_score if health else None
        )
        overview.append(metric)

    return overview


def get_user_summary(db: Session, user_id: int, target_date: date = None) -> dict:
    """
    Get user's core summary metrics for dashboard header.

    Args:
        db: Database session
        user_id: User ID to filter by
        target_date: Target date (defaults to today)

    Returns:
        Dictionary with summary data matching SummaryResponse schema

    Raises:
        ValueError: If user not found
    """
    if target_date is None:
        target_date = date.today()

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get health metric for target date
    health_metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == target_date
    ).first()

    # Get work metrics aggregated for target date
    work_metrics = db.query(
        func.sum(WorkMetric.screen_time_minutes).label('total_minutes'),
        func.avg(WorkMetric.focus_score).label('avg_focus')
    ).filter(
        WorkMetric.user_id == user_id,
        func.date(WorkMetric.timestamp) == target_date
    ).first()

    summary = {
        'date': target_date,
        'user_id': user.id,
        'user_name': user.name,
        'avatar': user.avatar,
        'metrics': {
            'sleep_hours': health_metric.sleep_hours if health_metric else None,
            'steps': getattr(health_metric, 'steps', None) if health_metric else None,
            'calories': getattr(health_metric, 'calories', None) if health_metric else None,
            'work_hours': round(work_metrics.total_minutes / 60, 1) if work_metrics.total_minutes else None,
            'stress_level': health_metric.stress_level if health_metric else None,
        }
    }

    return summary


# ============ User Preference Functions ============

def get_user_preferences(db: Session, user_id: int) -> UserPreferenceResponse:
    """
    Get user preferences or return defaults if not set.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        UserPreferenceResponse object
    """
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).first()

    if preference:
        return UserPreferenceResponse(
            id=preference.id,
            user_id=preference.user_id,
            show_sleep=preference.show_sleep,
            show_exercise=preference.show_exercise,
            show_work_time=preference.show_work_time,
            show_focus=preference.show_focus,
            show_stress=preference.show_stress,
            show_sleep_stages=preference.show_sleep_stages,
            hidden_cards=preference.hidden_cards,
            default_view_tab=preference.default_view_tab,
            created_at=preference.created_at,
            updated_at=preference.updated_at
        )
    else:
        # Return default preferences
        return UserPreferenceResponse(
            id=0,
            user_id=user_id,
            show_sleep=1,
            show_exercise=1,
            show_work_time=1,
            show_focus=1,
            show_stress=1,
            show_sleep_stages=1,
            hidden_cards=None,
            default_view_tab='activity',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )


def update_user_preferences(db: Session, user_id: int, preferences: UserPreferenceUpdate) -> UserPreferenceResponse:
    """
    Update or create user preferences.

    Args:
        db: Database session
        user_id: User ID
        preferences: Preference data to update

    Returns:
        UserPreferenceResponse object
    """
    existing = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).first()

    if existing:
        # Update existing preferences
        existing.show_sleep = preferences.show_sleep
        existing.show_exercise = preferences.show_exercise
        existing.show_work_time = preferences.show_work_time
        existing.show_focus = preferences.show_focus
        existing.show_stress = preferences.show_stress
        existing.show_sleep_stages = preferences.show_sleep_stages
        # Update new fields if provided
        if preferences.hidden_cards is not None:
            existing.hidden_cards = preferences.hidden_cards
        if preferences.default_view_tab is not None:
            existing.default_view_tab = preferences.default_view_tab
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return UserPreferenceResponse(
            id=existing.id,
            user_id=existing.user_id,
            show_sleep=existing.show_sleep,
            show_exercise=existing.show_exercise,
            show_work_time=existing.show_work_time,
            show_focus=existing.show_focus,
            show_stress=existing.show_stress,
            show_sleep_stages=existing.show_sleep_stages,
            hidden_cards=existing.hidden_cards,
            default_view_tab=existing.default_view_tab,
            created_at=existing.created_at,
            updated_at=existing.updated_at
        )
    else:
        # Create new preferences
        from datetime import datetime
        new_preference = UserPreference(
            user_id=user_id,
            show_sleep=preferences.show_sleep,
            show_exercise=preferences.show_exercise,
            show_work_time=preferences.show_work_time,
            show_focus=preferences.show_focus,
            show_stress=preferences.show_stress,
            show_sleep_stages=preferences.show_sleep_stages,
            hidden_cards=preferences.hidden_cards,
            default_view_tab=preferences.default_view_tab
        )
        db.add(new_preference)
        db.commit()
        db.refresh(new_preference)
        return UserPreferenceResponse(
            id=new_preference.id,
            user_id=new_preference.user_id,
            show_sleep=new_preference.show_sleep,
            show_exercise=new_preference.show_exercise,
            show_work_time=new_preference.show_work_time,
            show_focus=new_preference.show_focus,
            show_stress=new_preference.show_stress,
            show_sleep_stages=new_preference.show_sleep_stages,
            hidden_cards=new_preference.hidden_cards,
            default_view_tab=new_preference.default_view_tab,
            created_at=new_preference.created_at,
            updated_at=new_preference.updated_at
        )
