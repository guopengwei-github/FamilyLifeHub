"""
Data aggregator for health report generation.

Collects and formats Garmin health data for morning and evening reports.
"""
from datetime import date, timedelta, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import User, HealthMetric, BodyStatusTimeseries, GarminActivity
from app.core.timezone import local_date_to_utc_range


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
        'user_profile': _get_user_profile(user),
        # 新增数据源
        'sleep_charging_efficiency': _get_sleep_charging_efficiency(db, user_id, report_date),
        'sleep_structure': _get_sleep_structure_analysis(db, user_id, report_date),
        'recovery_quality': _get_recovery_quality_score(db, user_id, report_date),
        'yesterday_workout': _get_yesterday_workout_data(db, user_id, report_date)
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
        'resting_hr': resting_hr,
        # 新增数据源
        'workout_data': _get_workout_data(db, user_id, report_date),
        'heart_rate_zones': _get_heart_rate_zones(db, user_id, report_date, user),
        'energy_curve': _get_energy_curve_analysis(db, user_id, report_date)
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
    # 时区转换
    utc_start, utc_end = local_date_to_utc_range(report_date)
    
    # Today's HR from timeseries
    today_data = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= utc_start,
        BodyStatusTimeseries.timestamp < utc_end
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
    # 时区转换
    utc_start, utc_end = local_date_to_utc_range(report_date)
    
    # Today's stress from timeseries
    today_data = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= utc_start,
        BodyStatusTimeseries.timestamp < utc_end
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
    """Get body battery consumption data.
    
    使用 HealthMetric.body_battery 而不是时间序列数据，
    避免因时区问题获取到昨天的数据。
    """
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()

    if not metric or metric.body_battery is None:
        return None

    # 直接使用 HealthMetric 中的身体电量
    # 这个值是当前最新的身体电量（通常是早晨醒来后的值）
    morning_value = metric.body_battery_before_sleep  # 睡前身体电量
    current_value = metric.body_battery  # 当前身体电量（早晨醒来后的值）
    
    # 如果没有睡前值，使用当前值作为 morning_value
    if morning_value is None:
        morning_value = current_value

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


# ============ 新增数据聚合函数（晚间报告增强） ============

def _get_workout_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """获取今日运动详情
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期
    
    Returns:
        包含运动列表的字典，或 None
    """
    activities = db.query(GarminActivity).filter(
        GarminActivity.user_id == user_id,
        GarminActivity.date == report_date
    ).order_by(GarminActivity.start_time_local).all()
    
    if not activities:
        return None
    
    workout_list = []
    for act in activities:
        workout = {
            'time': act.start_time_local.strftime('%H:%M') if act.start_time_local else 'N/A',
            'type': _activity_type_cn(act.activity_type or act.activity_type_key),
            'duration_min': round(act.duration_seconds / 60) if act.duration_seconds else None,
            'distance_km': round(act.distance_meters / 1000, 1) if act.distance_meters else None,
            'calories': int(act.calories) if act.calories else None,
            'avg_hr': int(act.average_heartrate) if act.average_heartrate else None,
            'max_hr': int(act.max_heartrate) if act.max_heartrate else None,
        }
        workout_list.append(workout)
    
    return {'workouts': workout_list}


def _activity_type_cn(type_key: str | None) -> str:
    """运动类型转中文名
    
    Args:
        type_key: Garmin 运动类型键
    
    Returns:
        中文名称
    """
    if not type_key:
        return '未知'
    
    mapping = {
        'running': '跑步',
        'cycling': '骑行',
        'swimming': '游泳',
        'strength_training': '力量训练',
        'weight_training': '力量训练',
        'yoga': '瑜伽',
        'walking': '步行',
        'hiking': '徒步',
        'elliptical': '椭圆机',
        'treadmill_running': '跑步机',
        'indoor_cardio': '室内有氧',
        'cardio': '有氧运动',
        'fitness_equipment': '健身器材',
        'crossfit': 'CrossFit',
        'rower': '划船机',
        'stair_climbing': '爬楼梯',
        'indoor_rowing': '室内划船',
    }
    
    return mapping.get(type_key.lower(), type_key)


def _get_heart_rate_zones(
    db: Session, 
    user_id: int, 
    report_date: date,
    user: User | None
) -> dict | None:
    """获取心率区间分布
    
    基于时间序列数据计算心率区间分布（分钟数）
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期（本地时间）
        user: User 对象（用于获取年龄计算最大心率）
    
    Returns:
        心率区间分布字典，或 None
    """
    # 时区转换
    utc_start, utc_end = local_date_to_utc_range(report_date)
    
    data = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= utc_start,
        BodyStatusTimeseries.timestamp < utc_end,
        BodyStatusTimeseries.heart_rate.isnot(None)
    ).all()
    
    if not data or len(data) < 10:
        return None
    
    # 计算最大心率：220 - 年龄（如果没有年龄，默认30岁）
    age = user.age if user and user.age else 30
    max_hr = 220 - age
    
    # 心率区间阈值
    zones = {
        'rest': 0,       # <60% 最大心率
        'fat_burn': 0,   # 60-70%
        'aerobic': 0,    # 70-80%
        'anaerobic': 0,  # 80-90%
        'extreme': 0     # >90%
    }
    
    zone_thresholds = {
        'rest': max_hr * 0.6,
        'fat_burn': max_hr * 0.7,
        'aerobic': max_hr * 0.8,
        'anaerobic': max_hr * 0.9,
    }
    
    for d in data:
        if d.heart_rate:
            hr = d.heart_rate
            if hr < zone_thresholds['rest']:
                zones['rest'] += 1
            elif hr < zone_thresholds['fat_burn']:
                zones['fat_burn'] += 1
            elif hr < zone_thresholds['aerobic']:
                zones['aerobic'] += 1
            elif hr < zone_thresholds['anaerobic']:
                zones['anaerobic'] += 1
            else:
                zones['extreme'] += 1
    
    # 转换为分钟（每条记录约3分钟）
    total_records = sum(zones.values())
    if total_records == 0:
        return None
    
    zone_minutes = {k: round(v * 3 / 60) for k, v in zones.items()}
    zone_percentages = {k: round(v / total_records * 100, 1) for k, v in zones.items()}
    
    return {
        'zones': zone_minutes,
        'percentages': zone_percentages,
        'max_hr': max_hr,
        'zone_thresholds': {
            'rest': f"<{int(zone_thresholds['rest'])} bpm",
            'fat_burn': f"{int(zone_thresholds['rest'])}-{int(zone_thresholds['fat_burn'])} bpm",
            'aerobic': f"{int(zone_thresholds['fat_burn'])}-{int(zone_thresholds['aerobic'])} bpm",
            'anaerobic': f"{int(zone_thresholds['aerobic'])}-{int(zone_thresholds['anaerobic'])} bpm",
            'extreme': f">{int(zone_thresholds['anaerobic'])} bpm",
        }
    }


def _get_energy_curve_analysis(db: Session, user_id: int, report_date: date) -> dict | None:
    """分析身体电量曲线
    
    识别全天关键时段、精力低谷、快速消耗时段
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期（本地时间）
    
    Returns:
        能量曲线分析字典，或 None
    """
    # 时区转换
    utc_start, utc_end = local_date_to_utc_range(report_date)
    
    data = db.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= utc_start,
        BodyStatusTimeseries.timestamp < utc_end,
        BodyStatusTimeseries.body_battery.isnot(None)
    ).order_by(BodyStatusTimeseries.timestamp).all()
    
    if not data or len(data) < 10:
        return None
    
    # 按小时分组分析
    segments = []
    current_hour = None
    hour_data = []
    
    for d in data:
        # 将 UTC 时间转换为本地时间
        local_ts = d.timestamp + LOCAL_TZ_OFFSET
        hour = local_ts.hour
        
        if current_hour is None:
            current_hour = hour
            hour_data = [d]
        elif hour == current_hour:
            hour_data.append(d)
        else:
            # 处理上一小时的数据
            if len(hour_data) >= 2:
                segment = _analyze_hour_segment(hour_data)
                if segment:
                    segments.append(segment)
            current_hour = hour
            hour_data = [d]
    
    # 处理最后一小时
    if len(hour_data) >= 2:
        segment = _analyze_hour_segment(hour_data)
        if segment:
            segments.append(segment)
    
    # 找出最低点和快速消耗时段
    bb_values = [(d.body_battery, d.timestamp + LOCAL_TZ_OFFSET) for d in data if d.body_battery is not None]
    if not bb_values:
        return None
    
    min_bb = min(bb_values, key=lambda x: x[0])
    max_drop_segment = min(segments, key=lambda x: x['bb_change']) if segments else None
    
    # 识别精力低谷时段（电量 < 30）
    low_energy_periods = []
    for seg in segments:
        if seg['end_bb'] is not None and seg['end_bb'] < 30:
            low_energy_periods.append({
                'time': seg['time_range'],
                'value': seg['end_bb']
            })
    
    return {
        'segments': segments,
        'lowest_point': {
            'time': min_bb[1].strftime('%H:%M'),
            'value': min_bb[0]
        },
        'fastest_drop': max_drop_segment,
        'low_energy_periods': low_energy_periods
    }


def _analyze_hour_segment(hour_data: list) -> dict | None:
    """分析一小时的电量变化
    
    Args:
        hour_data: 一小时内的 BodyStatusTimeseries 记录列表
    
    Returns:
        时段分析字典，或 None
    """
    if not hour_data or len(hour_data) < 2:
        return None
    
    first = hour_data[0]
    last = hour_data[-1]
    
    start_bb = first.body_battery
    end_bb = last.body_battery
    
    if start_bb is None or end_bb is None:
        return None
    
    bb_change = end_bb - start_bb
    
    # 计算平均压力
    stress_values = [d.stress_level for d in hour_data if d.stress_level is not None]
    avg_stress = round(sum(stress_values) / len(stress_values)) if stress_values else None
    
    # 计算平均心率
    hr_values = [d.heart_rate for d in hour_data if d.heart_rate is not None]
    avg_hr = round(sum(hr_values) / len(hr_values)) if hr_values else None
    
    # 转换为本地时间
    local_first = first.timestamp + LOCAL_TZ_OFFSET
    local_last = last.timestamp + LOCAL_TZ_OFFSET
    
    return {
        'time_range': f"{local_first.strftime('%H:%M')}-{local_last.strftime('%H:%M')}",
        'start_bb': start_bb,
        'end_bb': end_bb,
        'bb_change': bb_change,
        'avg_stress': avg_stress,
        'avg_hr': avg_hr,
    }


# ============ 新增数据聚合函数（早报增强） ============

def _get_sleep_charging_efficiency(db: Session, user_id: int, report_date: date) -> dict | None:
    """计算睡眠充电效率
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期
    
    Returns:
        睡眠充电效率字典，或 None
    """
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()
    
    if not metric:
        return None
    
    # 获取睡眠时长和充电量
    sleep_hours = metric.sleep_hours
    before_sleep = metric.body_battery_before_sleep
    after_sleep = metric.body_battery
    
    if sleep_hours is None or before_sleep is None or after_sleep is None:
        return None
    
    charged = after_sleep - before_sleep
    
    # 计算每小时充电速率
    charge_rate = round(charged / sleep_hours, 1) if sleep_hours > 0 else 0
    
    # 评估充电效率
    # 正常：每小时充电 8-12 点
    # 高效：每小时充电 > 12 点
    # 低效：每小时充电 < 8 点
    if charge_rate >= 12:
        efficiency = '高效'
    elif charge_rate >= 8:
        efficiency = '正常'
    else:
        efficiency = '低效'
    
    # 获取 7 日平均充电效率
    start_date = report_date - timedelta(days=8)
    past_metrics = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date >= start_date,
        HealthMetric.date < report_date
    ).all()
    
    charge_rates = []
    for m in past_metrics:
        if m.sleep_hours and m.body_battery_before_sleep is not None and m.body_battery is not None:
            past_charged = m.body_battery - m.body_battery_before_sleep
            if m.sleep_hours > 0:
                charge_rates.append(past_charged / m.sleep_hours)
    
    avg_charge_rate = round(sum(charge_rates) / len(charge_rates), 1) if charge_rates else None
    
    return {
        'sleep_hours': round(sleep_hours, 1),
        'charged': charged,
        'charge_rate': charge_rate,  # 每小时充电点数
        'efficiency': efficiency,
        'avg_7d_charge_rate': avg_charge_rate
    }


def _get_sleep_structure_analysis(db: Session, user_id: int, report_date: date) -> dict | None:
    """分析睡眠结构
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期
    
    Returns:
        睡眠结构分析字典，或 None
    """
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()
    
    if not metric or not metric.sleep_hours:
        return None
    
    total_sleep = metric.sleep_hours
    deep_sleep = metric.deep_sleep_hours or 0
    light_sleep = metric.light_sleep_hours or 0
    rem_sleep = metric.rem_sleep_hours or 0
    
    # 计算各阶段占比
    deep_pct = round(deep_sleep / total_sleep * 100, 1) if total_sleep > 0 else 0
    light_pct = round(light_sleep / total_sleep * 100, 1) if total_sleep > 0 else 0
    rem_pct = round(rem_sleep / total_sleep * 100, 1) if total_sleep > 0 else 0
    
    # 评估睡眠结构（理想比例：深睡 15-25%, 浅睡 50-60%, REM 20-25%）
    structure_quality = []
    
    if deep_pct < 10:
        structure_quality.append('深睡不足')
    elif deep_pct > 30:
        structure_quality.append('深睡过多')
    
    if rem_pct < 15:
        structure_quality.append('REM不足')
    elif rem_pct > 30:
        structure_quality.append('REM过多')
    
    if not structure_quality:
        structure_quality.append('睡眠结构正常')
    
    return {
        'total_sleep_hours': round(total_sleep, 1),
        'deep_sleep': {
            'hours': round(deep_sleep, 1),
            'percentage': deep_pct
        },
        'light_sleep': {
            'hours': round(light_sleep, 1),
            'percentage': light_pct
        },
        'rem_sleep': {
            'hours': round(rem_sleep, 1),
            'percentage': rem_pct
        },
        'structure_quality': structure_quality,
        'ideal_ranges': {
            'deep': '15-25%',
            'light': '50-60%',
            'rem': '20-25%'
        }
    }


def _get_recovery_quality_score(db: Session, user_id: int, report_date: date) -> dict | None:
    """计算恢复质量评分
    
    综合评估：睡眠质量、HRV、静息心率、身体电量充电
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期
    
    Returns:
        恢复质量评分字典，或 None
    """
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()
    
    if not metric:
        return None
    
    scores = []
    
    # 1. 睡眠评分 (0-100)
    if metric.sleep_score:
        scores.append(('sleep', metric.sleep_score, 0.3))  # 权重 30%
    
    # 2. HRV 评分 (基于 7 日趋势)
    if metric.hrv_last_night:
        # 获取 7 日平均
        start_date = report_date - timedelta(days=8)
        past_metrics = db.query(HealthMetric).filter(
            HealthMetric.user_id == user_id,
            HealthMetric.date >= start_date,
            HealthMetric.date < report_date
        ).all()
        
        hrv_values = [m.hrv_last_night for m in past_metrics if m.hrv_last_night]
        if hrv_values:
            avg_hrv = sum(hrv_values) / len(hrv_values)
            # HRV 高于平均 = 恢复好
            hrv_ratio = metric.hrv_last_night / avg_hrv if avg_hrv > 0 else 1
            hrv_score = min(100, int(hrv_ratio * 80))  # 80 为基准分
            scores.append(('hrv', hrv_score, 0.25))  # 权重 25%
    
    # 3. 身体电量充电评分
    if metric.body_battery_before_sleep is not None and metric.body_battery is not None:
        charged = metric.body_battery - metric.body_battery_before_sleep
        # 充电 60+ 点 = 优秀, 40-60 = 良好, <40 = 一般
        if charged >= 60:
            bb_score = 90
        elif charged >= 40:
            bb_score = 70
        else:
            bb_score = 50
        scores.append(('body_battery', bb_score, 0.25))  # 权重 25%
    
    # 4. 静息心率评分
    if metric.resting_hr:
        # 获取 7 日平均
        start_date = report_date - timedelta(days=8)
        past_metrics = db.query(HealthMetric).filter(
            HealthMetric.user_id == user_id,
            HealthMetric.date >= start_date,
            HealthMetric.date < report_date
        ).all()
        
        hr_values = [m.resting_hr for m in past_metrics if m.resting_hr]
        if hr_values:
            avg_hr = sum(hr_values) / len(hr_values)
            # 静息心率低于平均 = 恢复好
            hr_ratio = avg_hr / metric.resting_hr if metric.resting_hr > 0 else 1
            hr_score = min(100, int(hr_ratio * 80))
            scores.append(('resting_hr', hr_score, 0.20))  # 权重 20%
    
    # 计算综合评分
    if not scores:
        return None
    
    total_weight = sum(s[2] for s in scores)
    weighted_score = sum(s[1] * s[2] for s in scores) / total_weight if total_weight > 0 else 0
    overall_score = round(weighted_score)
    
    # 评估恢复等级
    if overall_score >= 80:
        recovery_level = '优秀'
    elif overall_score >= 60:
        recovery_level = '良好'
    elif overall_score >= 40:
        recovery_level = '一般'
    else:
        recovery_level = '较差'
    
    return {
        'overall_score': overall_score,
        'recovery_level': recovery_level,
        'components': {s[0]: s[1] for s in scores}
    }


def _get_yesterday_workout_data(db: Session, user_id: int, report_date: date) -> dict | None:
    """获取昨日运动数据
    
    分析昨天运动对睡眠的影响
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期
    
    Returns:
        昨日运动数据字典，或 None
    """
    yesterday = report_date - timedelta(days=1)
    
    # 获取昨天的运动记录
    activities = db.query(GarminActivity).filter(
        GarminActivity.user_id == user_id,
        GarminActivity.date == yesterday
    ).order_by(GarminActivity.start_time_local).all()
    
    if not activities:
        return None
    
    workout_list = []
    total_duration = 0
    total_calories = 0
    
    for act in activities:
        workout = {
            'type': _activity_type_cn(act.activity_type or act.activity_type_key),
            'time': act.start_time_local.strftime('%H:%M') if act.start_time_local else 'N/A',
            'duration_min': round(act.duration_seconds / 60) if act.duration_seconds else 0,
            'calories': int(act.calories) if act.calories else 0,
            'avg_hr': int(act.average_heartrate) if act.average_heartrate else None,
            'max_hr': int(act.max_heartrate) if act.max_heartrate else None,
        }
        workout_list.append(workout)
        total_duration += workout['duration_min']
        total_calories += workout['calories']
    
    return {
        'date': str(yesterday),
        'workouts': workout_list,
        'total_duration_min': total_duration,
        'total_calories': total_calories,
        'workout_count': len(workout_list)
    }
