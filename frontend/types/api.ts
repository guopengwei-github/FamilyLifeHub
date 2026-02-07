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
}

// ============ Work Types ============

export interface WorkMetric {
  id: number;
  user_id: number;
  timestamp: string;
  screen_time_minutes: number | null;
  focus_score: number | null;
  active_window_category: string | null;
  created_at: string;
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
  total_work_minutes: number | null;
  avg_focus_score: number | null;
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
  total_work_minutes: number | null;
  avg_focus_score: number | null;
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
  is_cn?: boolean;  // True for China, False for International
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
  errors: string[];
  last_sync_at: string | null;
}

// ============ Strava Types ============

export interface StravaAppConfig {
  client_id: string;
  client_secret: string;
}

export interface StravaAppConfigResponse {
  has_config: boolean;
}

export interface StravaConnection {
  connected: boolean;
  athlete_name: string | null;
  athlete_id: number | null;
  athlete_profile: string | null;
  created_at: string | null;
  last_sync_at: string | null;
  sync_status: string;
}

export interface StravaActivity {
  id: number;
  user_id: number;
  strava_activity_id: number | null;
  date: string;
  activity_type: string | null;
  name: string | null;
  distance_meters: number | null;
  moving_time_seconds: number | null;
  elapsed_time_seconds: number | null;
  average_speed_mps: number | null;
  max_speed_mps: number | null;
  average_heartrate: number | null;
  max_heartrate: number | null;
  elevation_gain_meters: number | null;
  calories: number | null;
  start_date: string | null;
  start_date_local: string | null;
  created_at: string;
}

export interface StravaActivitiesResponse {
  activities: StravaActivity[];
  count: number;
}

export interface StravaSyncRequest {
  days?: number;
  after_date?: string;
}

export interface StravaSyncResponse {
  success: boolean;
  activities_synced: number;
  metrics_updated: number;
  errors: string[];
  last_sync_at: string | null;
}

// ============ User Preference Types ============

export interface UserPreference {
  id: number;
  user_id: number;
  show_sleep: number;
  show_exercise: number;
  show_work_time: number;
  show_focus: number;
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
  show_work_time?: number;
  show_focus?: number;
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
  work_hours: number | null;
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
  ACTIVITY_HEALTH: 'activity_health',
  WORK: 'work',
  STRESS: 'stress',
  TRENDS: 'trends'
} as const;

export type CardId = typeof CARD_IDS[keyof typeof CARD_IDS];
