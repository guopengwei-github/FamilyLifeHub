"""
SQLAlchemy database models for FamilyLifeHub.
All timestamps are stored in UTC.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class User(Base):
    """
    User model representing family members.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1, nullable=False)  # Boolean as integer for SQLite
    avatar = Column(String(255), nullable=True)  # URL or path to avatar image
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # User profile for health reports
    age = Column(Integer, nullable=True)           # 年龄 (deprecated: 从 birth_date 计算)
    gender = Column(String(10), nullable=True)     # 性别: 'male', 'female', 'other'
    weight_kg = Column(Float, nullable=True)       # 体重(kg)
    birth_date = Column(Date, nullable=True)       # 出生日期
    height_cm = Column(Float, nullable=True)       # 身高(cm)

    # Relationships
    health_metrics = relationship("HealthMetric", back_populates="user", cascade="all, delete-orphan")
    garmin_connection = relationship("GarminConnection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    user_preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    health_reports = relationship("HealthReport", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}')>"


class UserPreference(Base):
    """
    User preferences for dashboard metric visibility.
    One record per user.
    """
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Visibility flags (stored as integers for SQLite compatibility)
    show_sleep = Column(Integer, default=1, nullable=False)  # Show sleep metrics
    show_exercise = Column(Integer, default=1, nullable=False)  # Show exercise metrics
    show_stress = Column(Integer, default=1, nullable=False)  # Show stress level
    show_sleep_stages = Column(Integer, default=1, nullable=False)  # Show sleep stages breakdown

    # Card visibility settings
    hidden_cards = Column(Text, nullable=True)  # JSON string: 隐藏的卡片ID列表
    default_view_tab = Column(String(50), default='activity', nullable=False)  # 默认Tab: activity/health

    # Timestamps
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_preferences")

    def __repr__(self):
        return f"<UserPreference(user_id={self.user_id})>"


class HealthMetric(Base):
    """
    Health metrics from Garmin or manual input.
    One record per user per day.
    """
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)  # Date of the metric (UTC)

    # Health data fields
    sleep_hours = Column(Float, nullable=True)  # Total sleep in hours
    light_sleep_hours = Column(Float, nullable=True)  # Light sleep in hours
    deep_sleep_hours = Column(Float, nullable=True)  # Deep sleep in hours
    rem_sleep_hours = Column(Float, nullable=True)  # REM sleep in hours
    resting_heart_rate = Column(Integer, nullable=True)  # BPM
    stress_level = Column(Integer, nullable=True)  # 0-100, derived from HRV
    exercise_minutes = Column(Integer, nullable=True)  # Total exercise time in minutes

    # Garmin advanced metrics
    steps = Column(Integer, nullable=True)  # 步数
    calories = Column(Integer, nullable=True)  # 卡路里消耗
    distance_km = Column(Float, nullable=True)  # 距离(公里)
    body_battery = Column(Integer, nullable=True)  # 身体电量 (0-100)
    spo2 = Column(Float, nullable=True)  # 血氧饱和度 (%)
    respiration_rate = Column(Float, nullable=True)  # 呼吸频率 (次/分)
    resting_hr = Column(Integer, nullable=True)  # 静息心率 (BPM)
    sleep_score = Column(Integer, nullable=True)  # 睡眠质量评分 (0-100)
    hrv_last_night = Column(Integer, nullable=True)  # 昨晚HRV平均值 (ms)
    hrv_weekly_avg = Column(Integer, nullable=True)  # 周平均HRV (ms)
    hrv_status = Column(String(50), nullable=True)  # HRV状态 (e.g., "balanced", "unbalanced")

    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="health_metrics")

    def __repr__(self):
        return f"<HealthMetric(user_id={self.user_id}, date={self.date})>"


class GarminConnection(Base):
    """
    Garmin Connect connection for syncing health data using community library.
    One connection per user.
    """
    __tablename__ = "garmin_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Credentials (encrypted)
    garmin_username = Column(Text, nullable=True)
    garmin_password = Column(Text, nullable=True)
    garmin_mfa_token = Column(Text, nullable=True)  # Deprecated: MFA tokens expire quickly, use OAuth tokens instead
    garmin_oauth_tokens = Column(Text, nullable=True)  # Serialized OAuth1/OAuth2 tokens from garth (base64)
    is_cn = Column(Integer, default=0, nullable=False)  # 0=International, 1=China

    # Garmin user info
    garmin_user_id = Column(String(255), nullable=True)
    garmin_display_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)
    last_sync_at = Column(DateTime, nullable=True)

    # Connection status
    sync_status = Column(String(50), default="connected", nullable=False)  # connected/error/expired
    last_error = Column(Text, nullable=True)  # Store last error message for debugging

    # Relationships
    user = relationship("User", back_populates="garmin_connection")

    def __repr__(self):
        return f"<GarminConnection(user_id={self.user_id}, status={self.sync_status})>"


class GarminActivity(Base):
    """
    Detailed activity data from Garmin Connect.
    Stores complete activity information including distance, duration, pace, heart rate, etc.
    """
    __tablename__ = "garmin_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    garmin_activity_id = Column(Integer, nullable=True, unique=True, index=True)

    # Activity details
    activity_type = Column(String(50), nullable=True)  # RUNNING, CYCLING, etc.
    activity_type_key = Column(String(50), nullable=True)  # Garmin's type key
    name = Column(String(255), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    distance_meters = Column(Float, nullable=True)
    calories = Column(Float, nullable=True)
    average_heartrate = Column(Float, nullable=True)
    max_heartrate = Column(Integer, nullable=True)
    avg_speed_mps = Column(Float, nullable=True)
    max_speed_mps = Column(Float, nullable=True)
    elevation_gain_meters = Column(Float, nullable=True)

    # Timestamps
    start_time = Column(DateTime, nullable=True)
    start_time_local = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<GarminActivity(user_id={self.user_id}, type={self.activity_type}, date={self.date})>"


class BodyStatusTimeseries(Base):
    """
    Time-series body status data from Garmin.
    Stores minute-level body battery, stress, and heart rate readings.
    """
    __tablename__ = "body_status_timeseries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Body status metrics
    body_battery = Column(Integer, nullable=True)  # 0-100
    stress_level = Column(Integer, nullable=True)  # 0-100
    heart_rate = Column(Integer, nullable=True)    # BPM

    __table_args__ = (
        Index('ix_body_status_user_timestamp', 'user_id', 'timestamp'),
    )

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<BodyStatusTimeseries(user_id={self.user_id}, timestamp={self.timestamp})>"


class HealthReport(Base):
    """
    LLM-generated health reports.
    Stores morning and evening reports generated from Garmin data.
    """
    __tablename__ = "health_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    report_type = Column(String(20), nullable=False)  # 'morning' or 'evening'

    input_context = Column(Text, nullable=True)   # LLM 输入（调试用）
    content = Column(Text, nullable=False)        # 报告内容（Markdown）

    generated_at = Column(DateTime, default=datetime.now(timezone.utc))
    llm_model = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)

    __table_args__ = (
        Index('uq_user_date_type', 'user_id', 'report_date', 'report_type', unique=True),
    )

    # Relationships
    user = relationship("User", back_populates="health_reports")

    def __repr__(self):
        return f"<HealthReport(user_id={self.user_id}, date={self.report_date}, type={self.report_type})>"
