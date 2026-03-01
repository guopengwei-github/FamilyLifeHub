/**
 * Type definitions for FamilyLifeHub API responses
 */

// ============ Auth Types ============

export interface User {
  id: number;
  name: string;
  email: string;
  avatar: string | null;
  created_at: string;
}

export interface UserRegister {
  name: string;
  email: string;
  password: string;
  avatar?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

// ============ Health Types ============

export interface HealthMetric {
  id: number;
  user_id: number;
  date: string;
  sleep_hours: number | null;
  light_sleep_hours: number | null;
  deep_sleep_hours: number | null;
  rem_sleep_hours: number | null;
  resting_heart_rate: number | null;
  stress_level: number | null;
  exercise_minutes: number | null;
  // Garmin advanced metrics
  steps?: number | null;
  calories?: number | null;
  distance_km?: number | null;
  body_battery?: number | null;
  spo2?: number | null;
  respiration_rate?: number | null;
  resting_hr?: number | null;
  sleep_score?: number | null;
  hrv_last_night?: number | null;
  hrv_weekly_avg?: number | null;
  hrv_status?: string | null;
  created_at: string;
  updated_at: string;
}

export interface HealthMetricForm {
  date: string;
  sleep_hours?: number;
  light_sleep_hours?: number;
  deep_sleep_hours?: number;
  rem_sleep_hours?: number;
  resting_heart_rate?: number;
  stress_level?: number;
  exercise_minutes?: number;
  steps?: number;
  calories?: number;
  distance_km?: number;
  body_battery?: number;
  spo2?: number;
  respiration_rate?: number;
  resting_hr?: number;
  sleep_score?: number;
  hrv_last_night?: number;
  hrv_weekly_avg?: number;
  hrv_status?: string;
}

// ============ Dashboard Types ============

export interface OverviewMetric {
  user_id: number;
  user_name: string;
  sleep_hours: number | null;
  light_sleep_hours: number | null;
  deep_sleep_hours: number | null;
  rem_sleep_hours: number | null;
  exercise_minutes: number | null;
  stress_level: number | null;
  // Garmin advanced metrics
  steps: number | null;
  calories: number | null;
  distance_km: number | null;
  body_battery: number | null;
  spo2: number | null;
  respiration_rate: number | null;
  resting_hr: number | null;
  sleep_score: number | null;
  hrv_last_night: number | null;
  hrv_weekly_avg: number | null;
  hrv_status: string | null;
}

export interface OverviewResponse {
  date: string;
  metrics: OverviewMetric[];
}

export interface DailyTrendData {
  date: string;
  user_id: number;
  user_name: string;
  sleep_hours: number | null;
  light_sleep_hours: number | null;
  deep_sleep_hours: number | null;
  rem_sleep_hours: number | null;
  exercise_minutes: number | null;
  stress_level: number | null;
  // Garmin advanced metrics
  steps: number | null;
  calories: number | null;
  distance_km: number | null;
  body_battery: number | null;
  spo2: number | null;
  respiration_rate: number | null;
  resting_hr: number | null;
  sleep_score: number | null;
  hrv_last_night: number | null;
  hrv_weekly_avg: number | null;
  hrv_status: string | null;
}

export interface TrendResponse {
  start_date: string;
  end_date: string;
  data: DailyTrendData[];
}

// ============ API Error Types ============

export interface ApiError {
  detail: string;
}

// ============ Garmin Types ============

export interface GarminConnection {
  connected: boolean;
  garmin_display_name: string | null;
  garmin_user_id: string | null;
  created_at: string | null;
  last_sync_at: string | null;
  sync_status: string;
}

export interface GarminLoginRequest {
  username: string;
  password: string;
  mfa_token?: string;
  is_cn: boolean;  // True for China, False for International (always sent by frontend)
  mfa_session_id?: string;  // MFA session ID for resuming login (server-side storage)
}

export interface GarminSyncRequest {
  days?: number;
  start_date?: string;
}

export interface GarminSyncResponse {
  success: boolean;
  days_synced: number;
  metrics_created: number;
  metrics_updated: number;
  activities_created?: number;
  errors: string[];
  last_sync_at: string | null;
}

export interface GarminActivity {
  id: number;
  user_id: number;
  date: string;
  garmin_activity_id: number | null;
  activity_type: string | null;
  activity_type_key: string | null;
  name: string | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  calories: number | null;
  average_heartrate: number | null;
  max_heartrate: number | null;
  avg_speed_mps: number | null;
  max_speed_mps: number | null;
  elevation_gain_meters: number | null;
  start_time: string | null;
  start_time_local: string | null;
  created_at: string;
}

export interface GarminActivitiesResponse {
  activities: GarminActivity[];
  count: number;
}

export interface GarminMfaVerifyRequest {
  mfa_token: string;
  mfa_session_id: string;
}

// ============ User Preference Types ============

export interface UserPreference {
  id: number;
  user_id: number;
  show_sleep: number;
  show_exercise: number;
  show_stress: number;
  show_sleep_stages: number;
  hidden_cards?: string | null;
  default_view_tab?: string;
  created_at: string;
  updated_at: string;
}

export interface UserPreferenceUpdate {
  show_sleep?: number;
  show_exercise?: number;
  show_stress?: number;
  show_sleep_stages?: number;
  hidden_cards?: string;
  default_view_tab?: string;
}

// ============ Dashboard Summary Types ============

export interface SummaryMetric {
  sleep_hours: number | null;
  steps: number | null;
  calories: number | null;
  stress_level: number | null;
}

export interface SummaryResponse {
  date: string;
  user_id: number;
  user_name: string;
  avatar: string | null;
  metrics: SummaryMetric;
}

// ============ Card IDs ============

export const CARD_IDS = {
  SLEEP: 'sleep',
  ACTIVITY: 'activity',
  BODY_STATUS: 'body_status',
  HRV: 'hrv',
  TRENDS: 'trends'
} as const;

export type CardId = typeof CARD_IDS[keyof typeof CARD_IDS];

// ============ Body Status Timeseries Types ============

export interface BodyStatusTimeseriesPoint {
  timestamp: string;
  body_battery: number | null;
  stress_level: number | null;
  heart_rate: number | null;
}

export interface BodyStatusTimeseriesResponse {
  user_id: number;
  date: string;
  requested_date: string | null;
  data: BodyStatusTimeseriesPoint[];
}
