"""
SQLAlchemy database models for FamilyLifeHub.
All timestamps are stored in UTC.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from datetime import datetime
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    health_metrics = relationship("HealthMetric", back_populates="user", cascade="all, delete-orphan")
    work_metrics = relationship("WorkMetric", back_populates="user", cascade="all, delete-orphan")
    garmin_connection = relationship("GarminConnection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    strava_connection = relationship("StravaConnection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    activity_metrics = relationship("ActivityMetric", back_populates="user", cascade="all, delete-orphan")
    user_preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

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
    show_work_time = Column(Integer, default=1, nullable=False)  # Show work time metrics
    show_focus = Column(Integer, default=1, nullable=False)  # Show focus score
    show_stress = Column(Integer, default=1, nullable=False)  # Show stress level
    show_sleep_stages = Column(Integer, default=1, nullable=False)  # Show sleep stages breakdown

    # Card visibility settings
    hidden_cards = Column(Text, nullable=True)  # JSON string: 隐藏的卡片ID列表
    default_view_tab = Column(String(50), default='activity', nullable=False)  # 默认Tab: activity/health

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="health_metrics")

    def __repr__(self):
        return f"<HealthMetric(user_id={self.user_id}, date={self.date})>"


class WorkMetric(Base):
    """
    Work metrics from desktop client (future C++ application).
    Multiple records per user per day (heartbeat packets).
    """
    __tablename__ = "work_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)  # UTC timestamp

    # Work data fields
    screen_time_minutes = Column(Integer, nullable=True)  # Active screen time
    focus_score = Column(Integer, nullable=True)  # 0-100, calculated by client
    active_window_category = Column(String(50), nullable=True)  # e.g., "coding", "browsing", "gaming"

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="work_metrics")

    def __repr__(self):
        return f"<WorkMetric(user_id={self.user_id}, timestamp={self.timestamp})>"


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)

    # Connection status
    sync_status = Column(String(50), default="connected", nullable=False)  # connected/error/expired
    last_error = Column(Text, nullable=True)  # Store last error message for debugging

    # Relationships
    user = relationship("User", back_populates="garmin_connection")

    def __repr__(self):
        return f"<GarminConnection(user_id={self.user_id}, status={self.sync_status})>"


class StravaConnection(Base):
    """
    Strava OAuth2 connection for syncing activity data.
    One connection per user.
    """
    __tablename__ = "strava_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Strava app credentials (encrypted) - each user can use their own app
    strava_client_id = Column(Text, nullable=True)
    strava_client_secret = Column(Text, nullable=True)

    # OAuth tokens (encrypted)
    strava_access_token = Column(Text, nullable=True)  # Made nullable - not set until user connects
    strava_refresh_token = Column(Text, nullable=True)  # Made nullable
    strava_token_expires_at = Column(Integer, nullable=True)  # Made nullable

    # Strava athlete info
    strava_athlete_id = Column(Integer, nullable=True)
    strava_athlete_name = Column(String(255), nullable=True)
    strava_athlete_profile = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)

    # Connection status
    sync_status = Column(String(50), default="connected", nullable=False)  # connected/error/expired
    last_error = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="strava_connection")

    def __repr__(self):
        return f"<StravaConnection(user_id={self.user_id}, status={self.sync_status})>"


class ActivityMetric(Base):
    """
    Detailed activity data from Strava.
    Stores complete activity information including distance, duration, pace, heart rate, etc.
    """
    __tablename__ = "activity_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strava_activity_id = Column(Integer, nullable=True, unique=True, index=True)  # Strava's activity ID
    date = Column(Date, nullable=False, index=True)
    activity_type = Column(String(50), nullable=True)  # Run, Ride, Swim, etc.
    name = Column(String(255), nullable=True)  # Activity name

    # Activity details
    distance_meters = Column(Float, nullable=True)  # Distance in meters
    moving_time_seconds = Column(Integer, nullable=True)  # Moving time in seconds
    elapsed_time_seconds = Column(Integer, nullable=True)  # Total elapsed time in seconds
    average_speed_mps = Column(Float, nullable=True)  # Average speed (meters/second)
    max_speed_mps = Column(Float, nullable=True)  # Maximum speed
    average_heartrate = Column(Float, nullable=True)  # Average heart rate (BPM)
    max_heartrate = Column(Integer, nullable=True)  # Maximum heart rate (BPM)
    elevation_gain_meters = Column(Float, nullable=True)  # Total elevation gain (meters)
    calories = Column(Float, nullable=True)  # Calories burned

    # Timestamps
    start_date = Column(DateTime, nullable=True)  # Activity start time (UTC)
    start_date_local = Column(DateTime, nullable=True)  # Activity start time (local)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="activity_metrics")

    def __repr__(self):
        return f"<ActivityMetric(user_id={self.user_id}, strava_id={self.strava_activity_id}, type={self.activity_type})>"
