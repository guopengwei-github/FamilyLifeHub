"""
Pydantic schemas for request validation and response serialization.
"""
from pydantic import BaseModel, Field, field_serializer, field_validator
from datetime import datetime, timezone
from datetime import date as date_type
from typing import Optional, List


# ============ User Schemas ============

class UserBase(BaseModel):
    """Base user schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="User's name")
    avatar: Optional[str] = Field(None, max_length=255, description="Avatar URL or path")


class UserCreate(UserBase):
    """Schema for creating a new user via API key (legacy)."""
    pass


class UserRegister(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1, max_length=100, description="User's name")
    email: str = Field(..., max_length=255, description="User's email address")
    password: str = Field(..., min_length=6, max_length=100, description="User's password")
    avatar: Optional[str] = Field(None, max_length=255, description="Avatar URL or path")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: str = Field(..., max_length=255, description="User's email address")
    password: str = Field(..., description="User's password")


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Schema for JWT token data."""
    user_id: int


class Token(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, max_length=100, description="New password")


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's name")
    avatar: Optional[str] = Field(None, max_length=255, description="Avatar URL or path")


# ============ Health Metric Schemas ============

class HealthMetricBase(BaseModel):
    """Base health metric schema."""
    date: date_type = Field(..., description="Date of the metric (YYYY-MM-DD)")
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Sleep hours (0-24)")
    light_sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Light sleep hours")
    deep_sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Deep sleep hours")
    rem_sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="REM sleep hours")
    resting_heart_rate: Optional[int] = Field(None, ge=30, le=200, description="Resting heart rate (BPM)")
    stress_level: Optional[int] = Field(None, ge=0, le=100, description="Stress level (0-100)")
    exercise_minutes: Optional[int] = Field(None, ge=0, description="Exercise minutes")
    steps: Optional[int] = Field(None, ge=0, description="Daily steps")
    calories: Optional[int] = Field(None, ge=0, description="Calories burned")
    distance_km: Optional[float] = Field(None, ge=0, description="Distance in kilometers")
    body_battery: Optional[int] = Field(None, ge=0, le=100, description="Body battery (0-100)")
    spo2: Optional[float] = Field(None, ge=0, le=100, description="Blood oxygen saturation (%)")
    respiration_rate: Optional[float] = Field(None, ge=0, le=100, description="Respiration rate (breaths/min)")
    resting_hr: Optional[int] = Field(None, ge=30, le=200, description="Resting heart rate (BPM)")
    sleep_score: Optional[int] = Field(None, ge=0, le=100, description="Sleep quality score (0-100)")
    hrv_last_night: Optional[int] = Field(None, ge=0, description="Last night HRV average (ms)")
    hrv_weekly_avg: Optional[int] = Field(None, ge=0, description="Weekly average HRV (ms)")
    hrv_status: Optional[str] = Field(None, max_length=50, description="HRV status (e.g., balanced, unbalanced)")


class HealthMetricCreate(HealthMetricBase):
    """Schema for creating/updating health metrics."""
    user_id: int = Field(..., description="User ID")


class HealthMetricResponse(HealthMetricBase):
    """Schema for health metric response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Dashboard Schemas ============

class DailyTrendData(BaseModel):
    """Daily aggregated data for trend visualization."""
    date: date_type
    user_id: int
    user_name: str
    sleep_hours: Optional[float] = None
    light_sleep_hours: Optional[float] = None
    deep_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    exercise_minutes: Optional[int] = None
    stress_level: Optional[int] = None
    # Garmin advanced metrics
    steps: Optional[int] = None
    calories: Optional[int] = None
    distance_km: Optional[float] = None
    body_battery: Optional[int] = None
    spo2: Optional[float] = None
    respiration_rate: Optional[float] = None
    resting_hr: Optional[int] = None
    sleep_score: Optional[int] = None
    hrv_last_night: Optional[int] = None
    hrv_weekly_avg: Optional[int] = None
    hrv_status: Optional[str] = None


class TrendResponse(BaseModel):
    """Response schema for dashboard trends endpoint."""
    start_date: date_type
    end_date: date_type
    data: List[DailyTrendData]


class OverviewMetric(BaseModel):
    """Today's overview metrics for a single user."""
    user_id: int
    user_name: str
    sleep_hours: Optional[float] = None
    light_sleep_hours: Optional[float] = None
    deep_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    exercise_minutes: Optional[int] = None
    stress_level: Optional[int] = None
    # Garmin advanced metrics
    steps: Optional[int] = None
    calories: Optional[int] = None
    distance_km: Optional[float] = None
    body_battery: Optional[int] = None
    spo2: Optional[float] = None
    respiration_rate: Optional[float] = None
    resting_hr: Optional[int] = None
    sleep_score: Optional[int] = None
    hrv_last_night: Optional[int] = None
    hrv_weekly_avg: Optional[int] = None
    hrv_status: Optional[str] = None


class OverviewResponse(BaseModel):
    """Response schema for dashboard overview endpoint."""
    date: date_type
    metrics: List[OverviewMetric]


# ============ Garmin Schemas ============

class GarminLoginRequest(BaseModel):
    """Schema for Garmin Connect login with username/password."""
    username: str = Field(..., min_length=1, max_length=255, description="Garmin Connect username (email)")
    password: str = Field(..., min_length=1, max_length=255, description="Garmin Connect password")
    mfa_token: Optional[str] = Field(None, max_length=10, description="Optional MFA token for 2FA")
    is_cn: bool = Field(False, description="True for China (garmin.cn), False for International (garmin.com)")
    mfa_session_id: Optional[str] = Field(None, description="MFA session ID for resuming login (server-side storage)")


class GarminMfaVerifyRequest(BaseModel):
    """Schema for Garmin MFA verification only (second step without credentials)."""
    mfa_token: str = Field(..., min_length=1, max_length=10, description="MFA verification code")
    mfa_session_id: str = Field(..., description="MFA session ID from initial login")


class GarminConnectionResponse(BaseModel):
    """Response schema for Garmin connection status."""
    connected: bool = Field(..., description="Whether Garmin is connected")
    garmin_display_name: Optional[str] = Field(None, description="Garmin display name")
    garmin_user_id: Optional[str] = Field(None, description="Garmin user ID")
    created_at: Optional[datetime] = Field(None, description="Connection created timestamp")
    last_sync_at: Optional[datetime] = Field(None, description="Last successful sync timestamp")
    sync_status: str = Field(..., description="Connection status: connected/error/expired")

    @field_serializer('created_at', 'last_sync_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime as ISO 8601 with UTC timezone."""
        if dt is None:
            return None
        # SQLite returns naive datetime (no timezone), treat it as UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class GarminSyncRequest(BaseModel):
    """Schema for triggering Garmin sync."""
    days: Optional[int] = Field(7, ge=1, le=30, description="Number of days to sync (1-30)")
    start_date: Optional[date_type] = Field(None, description="Start date (overrides days)")


class GarminSyncResponse(BaseModel):
    """Response schema for Garmin sync operation."""
    success: bool = Field(..., description="Whether sync was successful")
    days_synced: int = Field(..., description="Number of days synced")
    metrics_created: int = Field(..., description="Number of metrics created")
    metrics_updated: int = Field(..., description="Number of metrics updated")
    activities_created: int = Field(default=0, description="Number of activities created")
    errors: List[str] = Field(default_factory=list, description="Any errors during sync")
    last_sync_at: Optional[datetime] = Field(None, description="Timestamp of this sync")

    @field_serializer('last_sync_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime as ISO 8601 with UTC timezone."""
        if dt is None:
            return None
        # SQLite returns naive datetime (no timezone), treat it as UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


# ============ User Preference Schemas ============

class UserPreferenceBase(BaseModel):
    """Base user preference schema."""
    show_sleep: int = Field(1, ge=0, le=1, description="Show sleep metrics (0 or 1)")
    show_exercise: int = Field(1, ge=0, le=1, description="Show exercise metrics (0 or 1)")
    show_stress: int = Field(1, ge=0, le=1, description="Show stress level (0 or 1)")
    show_sleep_stages: int = Field(1, ge=0, le=1, description="Show sleep stages (0 or 1)")
    hidden_cards: Optional[str] = Field(None, description="JSON string of hidden card IDs")
    default_view_tab: str = Field('activity', description="Default view tab: activity or health")


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preferences."""
    pass


class UserPreferenceUpdate(UserPreferenceBase):
    """Schema for updating user preferences."""
    pass


class UserPreferenceResponse(UserPreferenceBase):
    """Response schema for user preferences."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Dashboard Summary Schemas (新增) ============

class SummaryMetric(BaseModel):
    """Core summary metric for dashboard header."""
    sleep_hours: Optional[float] = None
    steps: Optional[int] = None
    calories: Optional[int] = None
    stress_level: Optional[int] = None


class SummaryResponse(BaseModel):
    """Response schema for dashboard summary endpoint."""
    date: date_type
    user_id: int
    user_name: str
    avatar: Optional[str] = None
    metrics: SummaryMetric


# ============ Garmin Activity Schemas ============

class GarminActivityResponse(BaseModel):
    """Response schema for a single Garmin activity."""
    id: int
    user_id: int
    date: date_type
    garmin_activity_id: Optional[int] = None
    activity_type: Optional[str] = None
    activity_type_key: Optional[str] = None
    name: Optional[str] = None
    duration_seconds: Optional[float] = None
    distance_meters: Optional[float] = None
    calories: Optional[float] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[int] = None
    avg_speed_mps: Optional[float] = None
    max_speed_mps: Optional[float] = None
    elevation_gain_meters: Optional[float] = None
    start_time: Optional[datetime] = None
    start_time_local: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GarminActivitiesResponse(BaseModel):
    """Response schema for Garmin activities list."""
    activities: List[GarminActivityResponse]
    count: int


# ============ Body Status Timeseries Schemas ============

class BodyStatusTimeseriesPoint(BaseModel):
    """Single data point in body status timeseries."""
    timestamp: datetime
    body_battery: Optional[int] = None
    stress_level: Optional[int] = None
    heart_rate: Optional[int] = None

    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime, _info) -> str:
        """Ensure timestamp is serialized with UTC timezone suffix."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat()
        return dt.isoformat()


class BodyStatusTimeseriesResponse(BaseModel):
    """Response schema for body status timeseries endpoint."""
    user_id: int
    date: date_type
    requested_date: Optional[date_type] = None
    data: List[BodyStatusTimeseriesPoint]


# ============ Health Report Schemas ============

class HealthReportResponse(BaseModel):
    """Response schema for a single health report."""
    id: int
    user_id: int
    report_date: date_type
    report_type: str  # 'morning' or 'evening'
    content: str
    generated_at: datetime
    llm_model: Optional[str] = None

    class Config:
        from_attributes = True

    @field_serializer('generated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime as ISO 8601 with UTC timezone."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class HealthReportListResponse(BaseModel):
    """Response schema for health reports list."""
    reports: List[HealthReportResponse]
    count: int


class HealthReportRegenerateRequest(BaseModel):
    """Schema for regenerating a health report."""
    report_type: str = Field(..., description="Report type: 'morning' or 'evening'")
    report_date: Optional[date_type] = Field(None, description="Date to regenerate (defaults to today)")


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile (for health reports)."""
    birth_date: Optional[date_type] = Field(None, description="Birth date (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, description="Gender: 'male', 'female', or 'other'")
    weight_kg: Optional[float] = Field(None, ge=20, le=300, description="Weight in kilograms")
    height_cm: Optional[float] = Field(None, ge=50, le=300, description="Height in centimeters")


class UserProfileResponse(BaseModel):
    """Response schema for user profile."""
    birth_date: Optional[date_type] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None  # Calculated from birth_date

    class Config:
        from_attributes = True


# ============ SMTP Configuration Schemas ============

class SmtpConfigBase(BaseModel):
    """Base SMTP configuration schema."""
    smtp_host: str = Field(..., min_length=1, max_length=255, description="SMTP server host")
    smtp_port: int = Field(465, ge=1, le=65535, description="SMTP server port")
    smtp_user: str = Field(..., min_length=1, max_length=255, description="SMTP username")
    smtp_password: str = Field(..., min_length=1, description="SMTP password or app token")
    use_ssl: int = Field(1, ge=0, le=1, description="Use SSL/TLS (1) or STARTTLS (0)")
    sender_email: Optional[str] = Field(None, max_length=255, description="Sender email address")
    sender_name: Optional[str] = Field(None, max_length=100, description="Sender display name")


class SmtpConfigCreate(SmtpConfigBase):
    """Schema for creating SMTP configuration."""
    pass


class SmtpConfigUpdate(BaseModel):
    """Schema for updating SMTP configuration."""
    smtp_host: Optional[str] = Field(None, min_length=1, max_length=255)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = Field(None, min_length=1, max_length=255)
    smtp_password: Optional[str] = Field(None, min_length=1)
    use_ssl: Optional[int] = Field(None, ge=0, le=1)
    sender_email: Optional[str] = Field(None, max_length=255)
    sender_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class SmtpConfigResponse(BaseModel):
    """Response schema for SMTP configuration (password masked)."""
    id: int
    user_id: int
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str  # Will be masked in API response
    use_ssl: int
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    is_active: int
    last_test_at: Optional[datetime] = None
    last_test_status: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('smtp_password')
    def mask_password(self, password: str) -> str:
        """Mask password in response."""
        if not password:
            return ""
        if len(password) <= 4:
            return "****"
        return password[:2] + "****" + password[-2:]

    @field_serializer('last_test_at', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime as ISO 8601 with UTC timezone."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class SmtpTestRequest(BaseModel):
    """Schema for testing SMTP connection."""
    pass


class SmtpTestResponse(BaseModel):
    """Response schema for SMTP connection test."""
    success: bool
    message: str


# ============ User Notification Settings Schemas ============

class UserNotificationSettingsUpdate(BaseModel):
    """Schema for updating user notification settings."""
    mail_for_notification: Optional[str] = Field(None, max_length=255, description="Email for notifications")


class UserNotificationSettingsResponse(BaseModel):
    """Response schema for user notification settings."""
    mail_for_notification: Optional[str] = None

    class Config:
        from_attributes = True


# ============ Scheduler Log Schemas ============

class SchedulerLogResponse(BaseModel):
    """Response schema for scheduler log entry."""
    id: int
    task_name: str
    user_id: Optional[int] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime as ISO 8601 with UTC timezone."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class SchedulerLogListResponse(BaseModel):
    """Response schema for scheduler logs list."""
    logs: List[SchedulerLogResponse]
    count: int
