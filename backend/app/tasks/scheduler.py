"""
Scheduler for health report generation tasks.

Uses APScheduler to run morning and evening report generation
at scheduled times (09:00 and 22:00 respectively).
"""
import logging
from datetime import date
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import User, HealthReport
from app.services.llm.zhipu import ZhipuProvider
from app.services.report_generator import generate_morning_report, generate_evening_report
from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


def get_llm_provider() -> ZhipuProvider:
    """Get configured LLM provider."""
    return ZhipuProvider(
        api_key=settings.ZHIPU_API_KEY,
        model=settings.ZHIPU_MODEL,
        base_url=settings.ZHIPU_BASE_URL
    )


async def generate_morning_reports_job():
    """
    Generate morning reports for all active users.
    Runs daily at 09:00.
    """
    logger.info("Starting morning report generation job")
    db: Session = SessionLocal()
    llm_provider = get_llm_provider()

    try:
        users = db.query(User).filter(User.is_active == 1).all()
        today = date.today()

        for user in users:
            try:
                # Check if report already exists
                existing = db.query(HealthReport).filter(
                    HealthReport.user_id == user.id,
                    HealthReport.report_date == today,
                    HealthReport.report_type == 'morning'
                ).first()

                if existing:
                    logger.info(f"Morning report already exists for user {user.id}")
                    continue

                # Generate report
                report_data = await generate_morning_report(
                    db=db,
                    user_id=user.id,
                    report_date=today,
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

                logger.info(f"Generated morning report for user {user.id}")

            except Exception as e:
                logger.error(f"Failed to generate morning report for user {user.id}: {e}")
                db.rollback()

    finally:
        db.close()

    logger.info("Morning report generation job completed")


async def generate_evening_reports_job():
    """
    Generate evening reports for all active users.
    Runs daily at 22:00.
    """
    logger.info("Starting evening report generation job")
    db: Session = SessionLocal()
    llm_provider = get_llm_provider()

    try:
        users = db.query(User).filter(User.is_active == 1).all()
        today = date.today()

        for user in users:
            try:
                # Check if report already exists
                existing = db.query(HealthReport).filter(
                    HealthReport.user_id == user.id,
                    HealthReport.report_date == today,
                    HealthReport.report_type == 'evening'
                ).first()

                if existing:
                    logger.info(f"Evening report already exists for user {user.id}")
                    continue

                # Generate report
                report_data = await generate_evening_report(
                    db=db,
                    user_id=user.id,
                    report_date=today,
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

                logger.info(f"Generated evening report for user {user.id}")

            except Exception as e:
                logger.error(f"Failed to generate evening report for user {user.id}: {e}")
                db.rollback()

    finally:
        db.close()

    logger.info("Evening report generation job completed")


def start_scheduler():
    """Start the scheduler with report generation jobs."""
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    scheduler = AsyncIOScheduler()

    # Morning report: 09:00 daily
    scheduler.add_job(
        generate_morning_reports_job,
        trigger=CronTrigger(hour=9, minute=0),
        id='morning_report',
        misfire_grace_time=3600,  # 1 hour grace period
        replace_existing=True
    )

    # Evening report: 22:00 daily
    scheduler.add_job(
        generate_evening_reports_job,
        trigger=CronTrigger(hour=22, minute=0),
        id='evening_report',
        misfire_grace_time=3600,
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started with morning (09:00) and evening (22:00) report jobs")


def stop_scheduler():
    """Stop the scheduler."""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")
