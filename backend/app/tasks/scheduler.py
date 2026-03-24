"""
Scheduler for health report generation tasks.

Uses APScheduler to run morning and evening report generation
at scheduled times (10:00 and 21:00 respectively).
"""
import logging
from datetime import date
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional, Tuple

from app.core.database import SessionLocal
from app.models import User, HealthReport, GarminConnection
from app.services.llm.zhipu import ZhipuProvider
from app.services.report_generator import generate_morning_report, generate_evening_report
from app.services import garmin as garmin_service
from app.services.email_service import EmailService
from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


def get_llm_provider() -> ZhipuProvider:
    """Get configured LLM provider."""
    return ZhipuProvider(
        api_key=settings.zhipu_api_key,
        model=settings.zhipu_model,
        base_url=settings.zhipu_base_url
    )


def sync_garmin_data_for_user(db: Session, user_id: int) -> Tuple[bool, bool]:
    """
    Sync Garmin data for a specific user before report generation.

    Returns:
        Tuple of (sync_success: bool, has_sleep_data: bool)
        - sync_success: True if sync was successful or no Garmin connection exists
        - has_sleep_data: True if sleep data was found for yesterday
    """
    connection = db.query(GarminConnection).filter(
        GarminConnection.user_id == user_id,
        GarminConnection.sync_status == "connected"
    ).first()

    if not connection:
        logger.info(f"No active Garmin connection for user {user_id}, skipping sync")
        return True, False

    try:
        logger.info(f"Syncing Garmin data for user {user_id}")
        results = garmin_service.refresh_garmin_data(
            user_id=user_id,
            days=1,  # Only sync today's data
            db_session=db
        )

        if results['success']:
            logger.info(f"Garmin sync completed for user {user_id}: {results['metrics_created']} created, {results['metrics_updated']} updated")
            
            # 检查是否有睡眠数据
            from app.models import HealthMetric
            from datetime import date, timedelta
            yesterday = date.today() - timedelta(days=1)
            
            sleep_data = db.query(HealthMetric).filter(
                HealthMetric.user_id == user_id,
                HealthMetric.date == yesterday,
                HealthMetric.sleep_hours.isnot(None)
            ).first()
            
            has_sleep = sleep_data is not None
            logger.info(f"Sleep data for yesterday: {'found' if has_sleep else 'not found'}")
            
            return True, has_sleep
        else:
            logger.warning(f"Garmin sync had errors for user {user_id}: {results['errors']}")
            return False, False

    except Exception as e:
        logger.error(f"Garmin sync failed for user {user_id}: {e}")
        return False, False


async def generate_morning_reports_job():
    """
    Generate morning reports for all active users.
    Runs daily at 09:00.
    
    Flow:
    1. Sync Garmin data for all users
    2. Check if sleep data exists for yesterday
    3. If yes, generate report and send email
    4. If no, send QQ notification to admin
    """
    logger.info("Starting morning report generation job")
    db: Session = SessionLocal()
    llm_provider = get_llm_provider()
    
    # QQ提醒配置（管理员QQ）
    ADMIN_QQ_ID = "D5F3791BBE73D631C4652D648CF4D9EC"
    
    try:
        users = db.query(User).filter(User.is_active == 1).all()
        today = date.today()

        for user in users:
            try:
                # Sync Garmin data first
                sync_success, has_sleep_data = sync_garmin_data_for_user(db, user.id)
                
                # 检查同步结果
                if not sync_success:
                    # 同步失败，发送QQ提醒
                    from app.services.qq_service import QQService
                    await QQService.send_message(
                        ADMIN_QQ_ID,
                        f"⚠️ Garmin数据同步失败\n\n"
                        f"用户：{user.name}\n"
                        f"时间：{today.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"请检查 Garmin 连接状态"
                    )
                    continue
                
                if not has_sleep_data:
                    # 没有睡眠数据，发送QQ提醒
                    from app.services.qq_service import QQService
                    await QQService.send_message(
                        ADMIN_QQ_ID,
                        f"⚠️ 未找到昨晚的睡眠数据\n\n"
                        f"用户：{user.name}\n"
                        f"日期：{(today - timedelta(days=1)).strftime('%Y-%m-%d')}\n"
                        f"无法生成早报，请检查数据源"
                    )
                    continue

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

                # Send email notification
                try:
                    success, message = EmailService.send_report_notification(
                        db=db,
                        user_id=user.id,
                        report_type='morning',
                        report_date=str(today),
                        report_content=report_data['content']
                    )
                    if success:
                        logger.info(f"Morning report email sent to user {user.id}")
                    else:
                        logger.warning(f"Failed to send morning report email to user {user.id}: {message}")
                except Exception as e:
                    logger.error(f"Error sending morning report email to user {user.id}: {e}")

            except Exception as e:
                logger.error(f"Failed to generate morning report for user {user.id}: {e}")
                db.rollback()

    finally:
        db.close()

    logger.info("Morning report generation job completed")


async def generate_evening_reports_job():
    """
    Generate evening reports for all active users.
    Runs daily at 21:00.
    """
    logger.info("Starting evening report generation job")
    db: Session = SessionLocal()
    llm_provider = get_llm_provider()

    try:
        users = db.query(User).filter(User.is_active == 1).all()
        today = date.today()

        for user in users:
            try:
                # Sync Garmin data first
                sync_success, _ = sync_garmin_data_for_user(db, user.id)

                # 如果同步失败，直接中断，不继续处理
                if not sync_success:
                    logger.error(f"Garmin sync failed for user {user.id}, skipping evening report generation")
                    continue

                # Check if report already exists
                existing = db.query(HealthReport).filter(
                    HealthReport.user_id == user.id,
                    HealthReport.report_date == today,
                    HealthReport.report_type == 'evening'
                ).first()

                # 如果已存在，删除并重新生成
                if existing:
                    logger.info(f"Evening report already exists for user {user.id}, deleting and regenerating")
                    db.delete(existing)
                    db.commit()

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

                # Send email notification
                try:
                    success, message = EmailService.send_report_notification(
                        db=db,
                        user_id=user.id,
                        report_type='evening',
                        report_date=str(today),
                        report_content=report_data['content']
                    )
                    if success:
                        logger.info(f"Evening report email sent to user {user.id}")
                    else:
                        logger.warning(f"Failed to send evening report email to user {user.id}: {message}")
                except Exception as e:
                    logger.error(f"Error sending evening report email to user {user.id}: {e}")

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

    # Evening report: 21:00 daily
    scheduler.add_job(
        generate_evening_reports_job,
        trigger=CronTrigger(hour=21, minute=0),
        id='evening_report',
        misfire_grace_time=3600,
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started with morning (10:00) and evening (21:00) report jobs")


def stop_scheduler():
    """Stop the scheduler."""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")
