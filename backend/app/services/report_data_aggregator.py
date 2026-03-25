"""
Data aggregator for health report generation.

Collects and formats Garmin health data for morning and evening reports.
"""
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import User, HealthMetric, BodyStatusTimeseries


def aggregate_morning_report_data(
    db: Session,
    user_id: int,
    report_date: date
) -> dict[str, Any]:
    """
    Aggregate data for morning readiness report.

    Args:
        db: Database session.
        user_id: User ID.
        report_date: Date of the report.

    Returns:
        Dictionary with sleep_data, hrv_data, body_battery, activity_data, user_profile, sleep_metrics.
    """
    user = db.query(User).filter(User.id == user_id).first()

    return {
        'sleep_data': _get_sleep_data(db, user_id, report_date),
        'hrv_data': _get_hrv_data(db, user_id, report_date),
        'body_battery': _get_morning_body_battery(db, user_id, report_date),
        'sleep_metrics': _get_sleep_period_metrics(db, user_id, report_date),
        'activity_data': _get_recent_activity_data(db, user_id, report_date),
        'user_profile': _get_user_profile(user)
    }


def aggregate_evening_report_data(
    db: Session,
    user_id: int,
    report_date: date
) -> dict[str, Any]:
    """
    Aggregate data for evening review report.

    Args:
        db: Database session.
        user_id: User ID.
        report_date: Date of the report.

    Returns:
        Dictionary with heart_rate_data, stress_data, body_battery, activity_data, user_profile, resting_hr.
    """
    user = db.query(User).filter(User.id == user_id).first()

    # Get resting HR from today's metric
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()
    resting_hr = metric.resting_hr if metric else None

    return {
        'heart_rate_data': _get_heart_rate_data(db, user_id, report_date),
        'stress_data': _get_stress_data(db, user_id, report_date),
        'body_battery': _get_evening_body_battery(db, user_id, report_date),
        'activity_data': _get_today_activity_data(db, user_id, report_date),
        'user_profile': _get_user_profile(user),
        'resting_hr': resting_hr
    }


def _get_user_profile(user: User | None) -> dict | None:
    """Extract user profile data."""
    if not user:
        return None

    profile = {}
    if user.age:
        profile['age'] = user.age
    if user.gender:
        profile['gender'] = user.gender
    if user.weight_kg:
        profile['weight_kg'] = user.weight_kg

    return profile if profile else None


def _get_sleep_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get sleep data for last night and 7-day trend.
    
    Note: Garmin dailySleepData API returns previous night's sleep when querying a date.
    So date=2026-03-25 contains sleep from the night of 3/24 (last night).
    We query report_date directly, not yesterday.
    """
    # Last night's sleep (Garmin stores it under today's date)
    last_night_metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    last_night = None
    if last_night_metric:
        last_night = {
            'total_sleep_hours': last_night_metric.sleep_hours,
            'deep_sleep_hours': last_night_metric.deep_sleep_hours,
            'light_sleep_hours': last_night_metric.light_sleep_hours,
            'rem_sleep_hours': last_night_metric.rem_sleep_hours,
            'sleep_score': last_night_metric.sleep_score
        }

    # 7-day average
    start_date = report_date - timedelta(days=8)
    metrics = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date >= start_date,
        HealthMetric.date < report_date
    ).all()

    sleep_hours_list = [m.sleep_hours for m in metrics if m.sleep_hours]
    avg_sleep = sum(sleep_hours_list) / len(sleep_hours_list) if sleep_hours_list else None

    return {
        'last_night': last_night,
        'trend_7d': {'avg_sleep_hours': round(avg_sleep, 1)} if avg_sleep else None
    }


def _get_hrv_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get HRV data with trends.
    
    Note: Garmin stores last night's HRV under today's date.
    """
    # Last night's HRV (stored under today's date)
    last_night_metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    # 7-day average
    start_date = report_date - timedelta(days=8)
    metrics = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date >= start_date,
        HealthMetric.date < report_date
    ).all()

    hrv_values = [m.hrv_last_night for m in metrics if m.hrv_last_night]
    avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else None

    # 3-day trend
    recent_hrv = hrv_values[:3] if len(hrv_values) >= 3 else hrv_values
    trend = None
    if len(recent_hrv) >= 2:
        if recent_hrv[0] > recent_hrv[-1]:
            trend = '上升'
        elif recent_hrv[0] < recent_hrv[-1]:
            trend = '下降'
        else:
            trend = '稳定'

    return {
        'last_night': {'avg_hrv': last_night_metric.hrv_last_night} if last_night_metric and last_night_metric.hrv_last_night else None,
        'avg_7d': round(avg_hrv) if avg_hrv else None,
        'trend_3d': trend
    }


def _get_morning_body_battery(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get morning body battery starting value with before/after sleep values."""
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    if not metric:
        return None

    result = {}

    if metric.body_battery is not None:
        result['morning_value'] = metric.body_battery
        result['after_sleep'] = metric.body_battery

    if metric.body_battery_before_sleep is not None:
        result['before_sleep'] = metric.body_battery_before_sleep

    # 计算睡眠充电量
    if 'before_sleep' in result and 'after_sleep' in result:
        result['charged'] = result['after_sleep'] - result['before_sleep']

    return result if result else None


def _get_sleep_period_metrics(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get sleep period metrics: SpO2, respiration rate, and stress during sleep.
    
    Note: Garmin stores last night's sleep metrics under today's date.
    """
    # Last night's sleep period metrics (stored under today's date)
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    if not metric:
        return None

    result = {}

    if metric.spo2 is not None:
        result['spo2'] = metric.spo2

    if metric.respiration_rate is not None:
        result['respiration_rate'] = metric.respiration_rate

    if metric.stress_level is not None:
        result['stress_level'] = metric.stress_level

    if metric.resting_hr is not None:
        result['resting_hr'] = metric.resting_hr

    return result if result else None


def _get_recent_activity_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get activity data for past 3 days."""
    start_date = report_date - timedelta(days=4)
    end_date = report_date - timedelta(days=1)

    metrics = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date >= start_date,
        HealthMetric.date <= end_date
    ).order_by(HealthMetric.date.desc()).all()

    days = []
    for m in metrics:
        if m.exercise_minutes and m.exercise_minutes > 0:
            days.append({
                'date': str(m.date),
                'activity_type': '运动',
                'duration_min': m.exercise_minutes
            })

    return {'days': days} if days else None


def _get_heart_rate_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get heart rate data with 7-day comparison."""
    # Today's HR from timeseries
    today_data = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= report_date
    ).all()

    today = None
    if today_data:
        hr_values = [d.heart_rate for d in today_data if d.heart_rate]
        if hr_values:
            today = {
                'avg_hr': round(sum(hr_values) / len(hr_values)),
                'max_hr': max(hr_values),
                'min_hr': min(hr_values)
            }

    # 7-day average
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    return {
        'today': today,
        'avg_7d': metric.resting_hr if metric else None
    }


def _get_stress_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get stress distribution with 7-day comparison."""
    # Today's stress from timeseries
    today_data = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= report_date
    ).all()

    today = None
    if today_data:
        stress_values = [d.stress_level for d in today_data if d.stress_level is not None]
        if stress_values:
            avg_stress = sum(stress_values) / len(stress_values)
            high = sum(1 for s in stress_values if s >= 60)
            medium = sum(1 for s in stress_values if 25 <= s < 60)
            low = sum(1 for s in stress_values if 0 <= s < 25)
            rest = sum(1 for s in stress_values if s < 0)

            today = {
                'avg_stress': round(avg_stress),
                'high_stress_minutes': high,
                'medium_stress_minutes': medium,
                'low_stress_minutes': low,
                'rest_stress_minutes': rest
            }

    # 7-day average
    start_date = report_date - timedelta(days=8)
    metrics = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date >= start_date,
        HealthMetric.date <= report_date
    ).all()

    stress_values = [m.stress_level for m in metrics if m.stress_level is not None]
    avg_7d = round(sum(stress_values) / len(stress_values)) if stress_values else None

    return {
        'today': today,
        'avg_7d': avg_7d
    }


def _get_evening_body_battery(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get body battery consumption data."""
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    if not metric:
        return None

    # Get timeseries for consumption calculation
    today_data = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= report_date
    ).order_by(BodyStatusTimeseries.timestamp).all()

    morning_value = None
    current_value = None

    if today_data:
        first = today_data[0]
        last = today_data[-1]
        if first.body_battery is not None:
            morning_value = first.body_battery
        if last.body_battery is not None:
            current_value = last.body_battery

    consumed = None
    if morning_value is not None and current_value is not None:
        consumed = morning_value - current_value

    # 3-day comparison
    start_date = report_date - timedelta(days=4)
    past_metrics = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date >= start_date,
        HealthMetric.date < report_date
    ).all()

    comparison_3d = None
    if past_metrics:
        bb_values = [m.body_battery for m in past_metrics if m.body_battery is not None]
        if bb_values:
            comparison_3d = round(sum(bb_values) / len(bb_values))

    return {
        'morning_value': morning_value,
        'current_value': current_value,
        'consumed': consumed,
        'comparison_3d': comparison_3d
    }


def _get_today_activity_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """Get today's activity data with 7-day comparison."""
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    today = None
    if metric:
        today = {
            'total_steps': metric.steps,
            'active_minutes': metric.exercise_minutes,
            'calories': metric.calories
        }

    # 7-day average
    start_date = report_date - timedelta(days=8)
    metrics = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date >= start_date,
        HealthMetric.date < report_date
    ).all()

    steps_values = [m.steps for m in metrics if m.steps]
    avg_7d = round(sum(steps_values) / len(steps_values)) if steps_values else None

    return {
        'today': today,
        'avg_7d': avg_7d
    }
