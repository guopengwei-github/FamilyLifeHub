"""
Pydantic schemas for request validation and response serialization.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
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


# ============ Work Metric Schemas ============

class WorkMetricBase(BaseModel):
    """Base work metric schema."""
    timestamp: datetime = Field(..., description="Timestamp of the metric (UTC)")
    screen_time_minutes: Optional[int] = Field(None, ge=0, description="Screen time in minutes")
    focus_score: Optional[int] = Field(None, ge=0, le=100, description="Focus score (0-100)")
    active_window_category: Optional[str] = Field(None, max_length=50, description="Active window category")

    @field_validator('active_window_category')
    @classmethod
    def validate_category(cls, v):
        """Validate active window category."""
        if v is not None:
            allowed_categories = ["coding", "browsing", "gaming", "communication", "productivity", "other"]
            if v.lower() not in allowed_categories:
                # Allow any category but normalize to lowercase
                return v.lower()
        return v


class WorkMetricCreate(WorkMetricBase):
    """Schema for creating work metrics."""
    user_id: int = Field(..., description="User ID")


class WorkMetricResponse(WorkMetricBase):
    """Schema for work metric response."""
    id: int
    user_id: int
    created_at: datetime

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
    total_work_minutes: Optional[int] = None
    avg_focus_score: Optional[float] = None
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
    total_work_minutes: Optional[int] = None
    avg_focus_score: Optional[float] = None
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


class GarminConnectionResponse(BaseModel):
    """Response schema for Garmin connection status."""
    connected: bool = Field(..., description="Whether Garmin is connected")
    garmin_display_name: Optional[str] = Field(None, description="Garmin display name")
    garmin_user_id: Optional[str] = Field(None, description="Garmin user ID")
    created_at: Optional[datetime] = Field(None, description="Connection created timestamp")
    last_sync_at: Optional[datetime] = Field(None, description="Last successful sync timestamp")
    sync_status: str = Field(..., description="Connection status: connected/error/expired")


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
    errors: List[str] = Field(default_factory=list, description="Any errors during sync")
    last_sync_at: Optional[datetime] = Field(None, description="Timestamp of this sync")


# ============ Strava Schemas ============

class StravaAppConfig(BaseModel):
    """Schema for user's Strava app credentials."""
    client_id: str = Field(..., min_length=1, description="Strava Client ID")
    client_secret: str = Field(..., min_length=1, description="Strava Client Secret")


class StravaAppConfigResponse(BaseModel):
    """Response schema for Strava app config status."""
    has_config: bool = Field(..., description="Whether user has configured Strava app credentials")


class StravaAuthUrlResponse(BaseModel):
    """Response schema for Strava authorization URL."""
    authorization_url: str = Field(..., description="OAuth authorization URL")


class StravaCallbackRequest(BaseModel):
    """Schema for Strava OAuth callback."""
    code: str = Field(..., description="Authorization code from Strava")
    state: Optional[str] = Field(None, description="Optional state parameter")


class StravaConnectionResponse(BaseModel):
    """Response schema for Strava connection status."""
    connected: bool = Field(..., description="Whether Strava is connected")
    athlete_name: Optional[str] = Field(None, description="Strava athlete name")
    athlete_id: Optional[int] = Field(None, description="Strava athlete ID")
    athlete_profile: Optional[str] = Field(None, description="Strava profile URL")
    created_at: Optional[datetime] = Field(None, description="Connection created timestamp")
    last_sync_at: Optional[datetime] = Field(None, description="Last successful sync timestamp")
    sync_status: str = Field(..., description="Connection status: connected/error/expired")


class StravaSyncRequest(BaseModel):
    """Schema for triggering Strava sync."""
    days: int = Field(30, ge=1, le=365, description="Number of days to sync (1-365)")
    after_date: Optional[date_type] = Field(None, description="Start date (overrides days)")


class StravaSyncResponse(BaseModel):
    """Response schema for Strava sync operation."""
    success: bool = Field(..., description="Whether sync was successful")
    activities_synced: int = Field(..., description="Number of activities synced")
    metrics_updated: int = Field(..., description="Number of health metrics updated")
    errors: List[str] = Field(default_factory=list, description="Any errors during sync")
    last_sync_at: Optional[datetime] = Field(None, description="Timestamp of this sync")


class StravaActivityResponse(BaseModel):
    """Response schema for a single Strava activity."""
    id: int
    user_id: int
    strava_activity_id: Optional[int] = None
    date: date_type
    activity_type: Optional[str] = None
    name: Optional[str] = None
    distance_meters: Optional[float] = None
    moving_time_seconds: Optional[int] = None
    elapsed_time_seconds: Optional[int] = None
    average_speed_mps: Optional[float] = None
    max_speed_mps: Optional[float] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[int] = None
    elevation_gain_meters: Optional[float] = None
    calories: Optional[float] = None
    start_date: Optional[datetime] = None
    start_date_local: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StravaActivitiesResponse(BaseModel):
    """Response schema for Strava activities list."""
    activities: List[StravaActivityResponse]
    count: int


# ============ User Preference Schemas ============

class UserPreferenceBase(BaseModel):
    """Base user preference schema."""
    show_sleep: int = Field(1, ge=0, le=1, description="Show sleep metrics (0 or 1)")
    show_exercise: int = Field(1, ge=0, le=1, description="Show exercise metrics (0 or 1)")
    show_work_time: int = Field(1, ge=0, le=1, description="Show work time metrics (0 or 1)")
    show_focus: int = Field(1, ge=0, le=1, description="Show focus score (0 or 1)")
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
    work_hours: Optional[float] = None
    stress_level: Optional[int] = None


class SummaryResponse(BaseModel):
    """Response schema for dashboard summary endpoint."""
    date: date_type
    user_id: int
    user_name: str
    avatar: Optional[str] = None
    metrics: SummaryMetric
