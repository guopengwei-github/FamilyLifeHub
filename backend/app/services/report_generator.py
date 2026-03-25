"""
Health report generator using LLM.

Generates morning and evening health reports by aggregating
Garmin data and sending to LLM for analysis.
"""
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.services.llm.base import LLMProvider
from app.services.llm.prompts import (
    GARMIN_DATA_GLOSSARY,
    MORNING_REPORT_SYSTEM_PROMPT,
    EVENING_REPORT_SYSTEM_PROMPT,
    format_morning_report_prompt,
    format_evening_report_prompt
)
from app.services.report_data_aggregator import (
    aggregate_morning_report_data,
    aggregate_evening_report_data
)


async def generate_morning_report(
    db: Session,
    user_id: int,
    report_date: date,
    llm_provider: LLMProvider
) -> dict[str, Any]:
    """
    Generate a morning readiness report.

    Args:
        db: Database session.
        user_id: User ID.
        report_date: Date of the report.
        llm_provider: LLM provider instance.

    Returns:
        Dictionary with report data including content and metadata.
    """
    # Aggregate data
    data = aggregate_morning_report_data(db, user_id, report_date)

    # Format prompt (新增参数)
    prompt = format_morning_report_prompt(
        report_date=report_date,
        sleep_data=data['sleep_data'],
        hrv_data=data['hrv_data'],
        body_battery=data['body_battery'],
        activity_data=data['activity_data'],
        user_profile=data['user_profile'],
        sleep_metrics=data.get('sleep_metrics'),
        # 新增数据源
        sleep_charging_efficiency=data.get('sleep_charging_efficiency'),
        sleep_structure=data.get('sleep_structure'),
        recovery_quality=data.get('recovery_quality'),
        yesterday_workout=data.get('yesterday_workout')
    )

    # Generate report
    content = await llm_provider.generate(
        prompt=prompt,
        system_prompt=GARMIN_DATA_GLOSSARY + MORNING_REPORT_SYSTEM_PROMPT,
        max_tokens=8192
    )

    return {
        'user_id': user_id,
        'report_date': report_date,
        'report_type': 'morning',
        'content': content,
        'input_context': prompt,
        'llm_model': llm_provider.model_name
    }


async def generate_evening_report(
    db: Session,
    user_id: int,
    report_date: date,
    llm_provider: LLMProvider
) -> dict[str, Any]:
    """
    Generate an evening review report.

    Args:
        db: Database session.
        user_id: User ID.
        report_date: Date of the report.
        llm_provider: LLM provider instance.

    Returns:
        Dictionary with report data including content and metadata.
    """
    # Aggregate data
    data = aggregate_evening_report_data(db, user_id, report_date)

    # Format prompt (新增参数)
    prompt = format_evening_report_prompt(
        report_date=report_date,
        heart_rate_data=data['heart_rate_data'],
        stress_data=data['stress_data'],
        body_battery=data['body_battery'],
        activity_data=data['activity_data'],
        user_profile=data['user_profile'],
        resting_hr=data.get('resting_hr'),
        # 新增数据源
        workout_data=data.get('workout_data'),
        heart_rate_zones=data.get('heart_rate_zones'),
        energy_curve=data.get('energy_curve')
    )

    # Generate report
    content = await llm_provider.generate(
        prompt=prompt,
        system_prompt=GARMIN_DATA_GLOSSARY + EVENING_REPORT_SYSTEM_PROMPT,
        max_tokens=8192
    )

    return {
        'user_id': user_id,
        'report_date': report_date,
        'report_type': 'evening',
        'content': content,
        'input_context': prompt,
        'llm_model': llm_provider.model_name
    }
