"""
Scheduler for health report generation tasks.

Uses APScheduler to run morning and evening report generation
at scheduled times (09:00 and 21:00 respectively).

Features:
- Automatic retry when Garmin data is stale (>2h old)
- Email notification to user when data needs update
- Maximum 3 retry attempts with 30-minute intervals
"""
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.models import User, HealthReport, GarminConnection, HealthMetric
from app.models.scheduler import ReportRetryLog
from app.services.llm.zhipu import ZhipuProvider
from app.services.report_generator import generate_morning_report, generate_evening_report
from app.services import garmin as garmin_service
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None

# 时区配置（Asia/Shanghai = UTC+8）
LOCAL_TZ_OFFSET = timedelta(hours=8)

# 从配置中读取重试参数
DATA_FRESHNESS_THRESHOLD_HOURS = settings.data_freshness_threshold_hours
RETRY_INTERVAL_MINUTES = settings.retry_interval_minutes
MAX_RETRY_COUNT = settings.max_retry_count


def get_llm_provider() -> ZhipuProvider:
    """Get configured LLM provider."""
    return ZhipuProvider(
        api_key=settings.zhipu_api_key,
        model=settings.zhipu_model,
        base_url=settings.zhipu_base_url
    )


def check_data_freshness(db: Session, user_id: int, report_date: date) -> Tuple[bool, Optional[datetime]]:
    """
    检查数据新鲜度
    
    Args:
        db: Database session
        user_id: User ID
        report_date: 报告日期
    
    Returns:
        Tuple of (is_fresh: bool, last_update_time: Optional[datetime])
        - is_fresh: True if data is less than 2 hours old
        - last_update_time: Last update time in local timezone (UTC+8), or None
    """
    # 获取健康数据
    metric = db.query(HealthMetric).filter(
        HealthMetric.user_id == user_id,
        HealthMetric.date == report_date
    ).first()
    
    if not metric or not metric.updated_at:
        logger.warning(f"No data or updated_at for user {user_id} on {report_date}")
        return False, None
    
    # 转换为本地时间（UTC+8）
    last_update_utc = metric.updated_at
    if last_update_utc.tzinfo is None:
        last_update_utc = last_update_utc.replace(tzinfo=timezone.utc)
    
    last_update_local = last_update_utc + LOCAL_TZ_OFFSET
    now_local = datetime.now(timezone.utc) + LOCAL_TZ_OFFSET
    
    # 计算数据年龄
    age = now_local - last_update_local
    is_fresh = age < timedelta(hours=DATA_FRESHNESS_THRESHOLD_HOURS)
    
    logger.info(
        f"Data freshness: user={user_id}, "
        f"last_update={last_update_local.strftime('%Y-%m-%d %H:%M:%S')}, "
        f"age={age}, is_fresh={is_fresh}"
    )
    
    return is_fresh, last_update_local


def sync_garmin_data_for_user(db: Session, user_id: int) -> Tuple[bool, bool, Optional[datetime]]:
    """
    Sync Garmin data for a specific user before report generation.

    Returns:
        Tuple of (sync_success: bool, has_sleep_data: bool, last_update_time: Optional[datetime])
        - sync_success: True if sync was successful or no Garmin connection exists
        - has_sleep_data: True if sleep data was found for last night
        - last_update_time: Last update time in local timezone, or None
    """
    connection = db.query(GarminConnection).filter(
        GarminConnection.user_id == user_id
    ).first()

    if not connection:
        logger.info(f"No Garmin connection for user {user_id}, skipping sync")
        return True, False, None

    try:
        logger.info(f"Syncing Garmin data for user {user_id}")
        results = garmin_service.refresh_garmin_data(
            user_id=user_id,
            days=1,  # Only sync today's data
            db_session=db
        )

        if results['success']:
            logger.info(
                f"Garmin sync completed for user {user_id}: "
                f"{results['metrics_created']} created, {results['metrics_updated']} updated"
            )
            
            # 检查是否有睡眠数据
            # 注意：Garmin 将昨晚的睡眠数据存储在今天的日期下
            today = date.today()
            
            sleep_data = db.query(HealthMetric).filter(
                HealthMetric.user_id == user_id,
                HealthMetric.date == today,
                HealthMetric.sleep_hours.isnot(None)
            ).first()
            
            has_sleep = sleep_data is not None
            logger.info(f"Sleep data for last night: {'found' if has_sleep else 'not found'}")
            
            # 获取最后更新时间
            _, last_update = check_data_freshness(db, user_id, today)
            
            return True, has_sleep, last_update
        else:
            logger.warning(f"Garmin sync had errors for user {user_id}: {results['errors']}")
            return False, False, None

    except Exception as e:
        logger.error(f"Garmin sync failed for user {user_id}: {e}")
        return False, False, None


async def schedule_report_retry(
    user_id: int,
    report_type: str,
    report_date: date,
    retry_count: int,
    last_update: Optional[datetime]
):
    """
    安排30分钟后的重试任务
    
    Args:
        user_id: User ID
        report_type: 'morning' or 'evening'
        report_date: 报告日期
        retry_count: 当前重试次数（从1开始）
        last_update: 数据最后更新时间
    """
    logger.info(f"Scheduling retry {retry_count}/{MAX_RETRY_COUNT} for {report_type} report, user {user_id}")
    
    # 计算下次重试时间
    next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=RETRY_INTERVAL_MINUTES)
    
    db = SessionLocal()
    try:
        # 检查是否已有重试记录
        existing = db.query(ReportRetryLog).filter(
            ReportRetryLog.user_id == user_id,
            ReportRetryLog.report_type == report_type,
            ReportRetryLog.report_date == report_date,
            ReportRetryLog.status == 'pending'
        ).first()
        
        if existing:
            # 更新现有记录
            existing.retry_count = retry_count
            existing.next_retry_at = next_retry_at
            existing.updated_at = datetime.now(timezone.utc)
            logger.info(f"Updated existing retry log: {existing}")
        else:
            # 创建新记录
            retry_log = ReportRetryLog(
                user_id=user_id,
                report_type=report_type,
                report_date=report_date,
                retry_count=retry_count,
                max_retries=MAX_RETRY_COUNT,
                next_retry_at=next_retry_at,
                status='pending'
            )
            db.add(retry_log)
            logger.info(f"Created new retry log: {retry_log}")
        
        db.commit()
        
        # 发送邮件提醒
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            EmailService.send_data_expired_notification(
                db=db,
                user=user,
                report_type=report_type,
                last_update=last_update,
                retry_count=retry_count,
                max_retries=MAX_RETRY_COUNT
            )
        
        # 添加一次性任务（30分钟后执行）
        job_id = f"retry_{report_type}_{user_id}_{report_date}_{retry_count}"
        
        # 确保scheduler已初始化
        if scheduler is None:
            logger.error("Scheduler not initialized, cannot schedule retry job")
            return
        
        scheduler.add_job(
            retry_report_generation,
            trigger=DateTrigger(run_date=next_retry_at),
            args=[user_id, report_type, report_date, retry_count],
            id=job_id,
            replace_existing=True
        )
        
        logger.info(f"Scheduled retry job: {job_id} at {next_retry_at}")
        
    except Exception as e:
        logger.error(f"Failed to schedule retry: {e}")
        db.rollback()
    finally:
        db.close()


async def retry_report_generation(
    user_id: int,
    report_type: str,
    report_date: date,
    retry_count: int
):
    """
    重试报告生成
    
    Args:
        user_id: User ID
        report_type: 'morning' or 'evening'
        report_date: 报告日期
        retry_count: 当前重试次数
    """
    logger.info(
        f"Retrying {report_type} report generation for user {user_id}, "
        f"attempt {retry_count}/{MAX_RETRY_COUNT}"
    )
    
    db = SessionLocal()
    llm_provider = get_llm_provider()
    ADMIN_QQ_ID = "D5F3791BBE73D631C4652D648CF4D9EC"
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return
        
        # 1. 再次同步 Garmin 数据
        sync_success, has_sleep_data, last_update = sync_garmin_data_for_user(db, user_id)
        
        if not sync_success:
            # 同步失败
            from app.services.qq_service import QQService
            await QQService.send_message(
                ADMIN_QQ_ID,
                f"⚠️ 重试同步失败\n\n"
                f"用户：{user.name}\n"
                f"报告类型：{report_type}\n"
                f"重试次数：{retry_count}/{MAX_RETRY_COUNT}\n"
                f"请检查 Garmin 连接状态"
            )
            return
        
        # 2. 检查数据新鲜度
        is_fresh, last_update = check_data_freshness(db, user_id, report_date)
        
        if not is_fresh:
            # 数据仍然过期
            if retry_count < MAX_RETRY_COUNT:
                # 继续重试
                await schedule_report_retry(
                    user_id,
                    report_type,
                    report_date,
                    retry_count + 1,
                    last_update
                )
                logger.info(f"Data still stale, scheduled retry {retry_count + 1}/{MAX_RETRY_COUNT}")
            else:
                # 已达最大重试次数，标记为失败
                retry_log = db.query(ReportRetryLog).filter(
                    ReportRetryLog.user_id == user_id,
                    ReportRetryLog.report_type == report_type,
                    ReportRetryLog.report_date == report_date,
                    ReportRetryLog.status == 'pending'
                ).first()
                
                if retry_log:
                    retry_log.status = 'failed'
                    retry_log.last_error = 'Max retries reached with stale data'
                    retry_log.updated_at = datetime.now(timezone.utc)
                    db.commit()
                
                # 发送最终失败通知
                from app.services.qq_service import QQService
                await QQService.send_message(
                    ADMIN_QQ_ID,
                    f"❌ 数据过期重试失败（已达{MAX_RETRY_COUNT}次上限）\n\n"
                    f"用户：{user.name}\n"
                    f"报告类型：{report_type}\n"
                    f"最后更新：{last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else 'N/A'}\n"
                    f"请手动检查 Garmin 连接"
                )
                logger.error(f"Max retries reached for user {user_id}")
            return
        
        # 3. 数据新鲜，生成报告
        logger.info(f"Data is fresh, generating {report_type} report for user {user_id}")
        
        # 检查报告是否已存在
        existing = db.query(HealthReport).filter(
            HealthReport.user_id == user_id,
            HealthReport.report_date == report_date,
            HealthReport.report_type == report_type
        ).first()
        
        if existing:
            logger.info(f"{report_type} report already exists, deleting and regenerating")
            db.delete(existing)
            db.commit()
        
        # 生成报告
        if report_type == 'morning':
            report_data = await generate_morning_report(
                db=db,
                user_id=user_id,
                report_date=report_date,
                llm_provider=llm_provider
            )
        else:
            report_data = await generate_evening_report(
                db=db,
                user_id=user_id,
                report_date=report_date,
                llm_provider=llm_provider
            )
        
        # 保存报告
        report = HealthReport(
            user_id=report_data['user_id'],
            report_date=report_data['report_date'],
            report_type=report_data['report_type'],
            content=report_data['content'],
            input_context=report_data['input_context'],
            llm_model=report_data['llm_model']
        )
        db.add(report)
        
        # 清理重试日志
        db.query(ReportRetryLog).filter(
            ReportRetryLog.user_id == user_id,
            ReportRetryLog.report_type == report_type,
            ReportRetryLog.report_date == report_date
        ).delete()
        
        db.commit()
        logger.info(f"✓ Successfully generated {report_type} report for user {user_id} after {retry_count} retries")
        
        # 发送邮件通知
        try:
            success, message = EmailService.send_report_notification(
                db=db,
                user_id=user_id,
                report_type=report_type,
                report_date=str(report_date),
                report_content=report_data['content']
            )
            if success:
                logger.info(f"Report email sent to user {user_id}")
            else:
                logger.warning(f"Failed to send report email: {message}")
        except Exception as e:
            logger.error(f"Error sending report email: {e}")
        
    except Exception as e:
        logger.error(f"Failed to retry {report_type} report for user {user_id}: {e}")
        db.rollback()
    finally:
        db.close()


async def generate_morning_reports_job():
    """
    Generate morning reports for all active users.
    Runs daily at 09:00.
    
    Flow:
    1. Sync Garmin data for all users
    2. Check if sleep data exists for yesterday
    3. Check data freshness (<2h old)
    4. If fresh: generate report and send email
    5. If stale: send email notification and schedule retry
    6. If no sleep data: send QQ notification to admin
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
                sync_success, has_sleep_data, last_update = sync_garmin_data_for_user(db, user.id)
                
                # 检查同步结果
                if not sync_success:
                    # 同步失败，发送QQ提醒
                    from app.services.qq_service import QQService
                    await QQService.send_message(
                        ADMIN_QQ_ID,
                        f"⚠️ Garmin数据同步失败\n\n"
                        f"用户：{user.name}\n"
                        f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
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
                
                # 检查数据新鲜度
                is_fresh, last_update = check_data_freshness(db, user.id, today)
                
                if not is_fresh:
                    # 数据过期，安排重试
                    logger.warning(f"Data is stale for user {user.id}, scheduling retry")
                    await schedule_report_retry(
                        user_id=user.id,
                        report_type='morning',
                        report_date=today,
                        retry_count=1,
                        last_update=last_update
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
    
    Flow:
    1. Sync Garmin data for all users
    2. Check data freshness (<2h old)
    3. If fresh: generate report and send email
    4. If stale: send email notification and schedule retry
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
                sync_success, _, last_update = sync_garmin_data_for_user(db, user.id)

                # 如果同步失败，直接中断，不继续处理
                if not sync_success:
                    logger.error(f"Garmin sync failed for user {user.id}, skipping evening report generation")
                    continue
                
                # 检查数据新鲜度
                is_fresh, last_update = check_data_freshness(db, user.id, today)
                
                if not is_fresh:
                    # 数据过期，安排重试
                    logger.warning(f"Data is stale for user {user.id}, scheduling retry")
                    await schedule_report_retry(
                        user_id=user.id,
                        report_type='evening',
                        report_date=today,
                        retry_count=1,
                        last_update=last_update
                    )
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
    logger.info("Scheduler started with morning (09:00) and evening (21:00) report jobs")


def stop_scheduler():
    """Stop the scheduler."""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")
