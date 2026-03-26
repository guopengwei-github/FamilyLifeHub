"""
统一的时区处理工具模块

确保整个项目中时区处理的一致性。
"""
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from typing import Tuple

# 使用明确的时区，而不是硬编码偏移
# 可以从环境变量或配置文件中读取
LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")  # UTC+8


def get_local_now() -> datetime:
    """
    获取当前本地时间（带时区）
    
    Returns:
        带时区信息的当前本地时间
    """
    return datetime.now(LOCAL_TIMEZONE)


def get_utc_now() -> datetime:
    """
    获取当前 UTC 时间
    
    Returns:
        当前 UTC 时间（带时区）
    """
    return datetime.now(timezone.utc)


def local_date_to_utc_range(local_date: date) -> Tuple[datetime, datetime]:
    """
    将本地日期转换为 UTC 查询范围
    
    Args:
        local_date: 本地日期
    
    Returns:
        (utc_start, utc_end) UTC 时间范围（带时区）
    
    Example:
        local_date = date(2026, 3, 26)  # 2026-03-26 本地时间
        utc_start, utc_end = local_date_to_utc_range(local_date)
        # utc_start = 2026-03-25 16:00:00 UTC (2026-03-26 00:00:00 +08:00)
        # utc_end = 2026-03-26 16:00:00 UTC (2026-03-27 00:00:00 +08:00)
    """
    # 本地日期的开始和结束时间
    local_start = datetime.combine(local_date, datetime.min.time(), tzinfo=LOCAL_TIMEZONE)
    local_end = local_start + timedelta(days=1)
    
    # 转换为 UTC
    utc_start = local_start.astimezone(timezone.utc)
    utc_end = local_end.astimezone(timezone.utc)
    
    return utc_start, utc_end


def utc_to_local(utc_datetime: datetime) -> datetime:
    """
    将 UTC 时间转换为本地时间
    
    Args:
        utc_datetime: UTC 时间（可以是 naive 或 aware）
    
    Returns:
        本地时间（带时区）
    """
    # 如果是 naive datetime，假设为 UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    
    return utc_datetime.astimezone(LOCAL_TIMEZONE)


def local_to_utc(local_datetime: datetime) -> datetime:
    """
    将本地时间转换为 UTC 时间
    
    Args:
        local_datetime: 本地时间（可以是 naive 或 aware）
    
    Returns:
        UTC 时间（带时区）
    """
    # 如果是 naive datetime，假设为本地时间
    if local_datetime.tzinfo is None:
        local_datetime = local_datetime.replace(tzinfo=LOCAL_TIMEZONE)
    
    return local_datetime.astimezone(timezone.utc)


def get_local_today() -> date:
    """
    获取当前本地日期
    
    Returns:
        当前本地日期
    """
    return get_local_now().date()


def format_local_datetime(dt: datetime) -> str:
    """
    格式化本地时间字符串
    
    Args:
        dt: datetime 对象
    
    Returns:
        格式化的时间字符串（本地时区）
    """
    local_dt = utc_to_local(dt) if dt.tzinfo == timezone.utc else dt
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')
