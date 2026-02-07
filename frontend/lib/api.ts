/**
 * API client for FamilyLifeHub backend
 */
import {
  OverviewResponse,
  TrendResponse,
  User,
  UserRegister,
  UserLogin,
  Token,
  HealthMetric,
  type HealthMetricForm as HealthMetricFormType,
  GarminConnection,
  GarminLoginRequest,
  GarminSyncResponse,
  StravaConnection,
  StravaActivity,
  StravaActivitiesResponse,
  StravaSyncResponse,
  UserPreference,
  type UserPreferenceUpdate as UserPreferenceUpdateType,
  type SummaryResponse,
  type CardId,
  CARD_IDS,
} from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

// ============ Token Management ============

/**
 * Get stored auth token from localStorage
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Set auth token in localStorage
 */
export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Remove auth token from localStorage
 */
export function clearAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Get stored user from localStorage
 */
export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    // Invalid JSON in localStorage, clear it
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

/**
 * Set user in localStorage
 */
function setStoredUser(user: User): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// ============ Fetch Helper ============

/**
 * Fetch wrapper with error handling and auth token
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit & { skipAuth?: boolean }
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const token = getAuthToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  // Add auth header if token exists and not skipping auth
  if (token && !options?.skipAuth) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // Handle 401 Unauthorized - clear token and redirect to login
      if (response.status === 401 && typeof window !== 'undefined') {
        clearAuthToken();
        if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
          window.location.href = '/login';
        }
      }

      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API Error (${endpoint}):`, error);
    throw error;
  }
}

// ============ Auth Endpoints ============

/**
 * Register a new user
 */
export async function register(data: UserRegister): Promise<Token> {
  const response = await fetchAPI<Token>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
    skipAuth: true,
  });

  // Store token and user
  setAuthToken(response.access_token);
  setStoredUser(response.user);

  return response;
}

/**
 * Login with email and password
 */
export async function login(data: UserLogin): Promise<Token> {
  const formData = new URLSearchParams();
  formData.append('username', data.email);
  formData.append('password', data.password);

  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });

  const response = await res.json() as Token;

  // Store token and user
  setAuthToken(response.access_token);
  setStoredUser(response.user);

  return response;
}

/**
 * Get current user profile
 */
export async function getCurrentUser(): Promise<User> {
  return fetchAPI<User>('/api/v1/auth/me');
}

/**
 * Logout (client-side only)
 */
export function logout(): void {
  clearAuthToken();
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
}

/**
 * Change password
 */
export async function changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
  return fetchAPI('/api/v1/auth/password', {
    method: 'PUT',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

// ============ Health Metric Endpoints ============

/**
 * List health metrics
 */
export async function listHealthMetrics(startDate?: string, endDate?: string): Promise<HealthMetric[]> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const endpoint = `/api/v1/health/metrics${params.toString() ? `?${params}` : ''}`;
  return fetchAPI<HealthMetric[]>(endpoint);
}

/**
 * Get health metric for a specific date
 */
export async function getHealthMetric(date: string): Promise<HealthMetric> {
  return fetchAPI<HealthMetric>(`/api/v1/health/metrics/${date}`);
}

/**
 * Create or upsert a health metric
 */
export async function createHealthMetric(data: HealthMetricFormType): Promise<HealthMetric> {
  return fetchAPI<HealthMetric>('/api/v1/health/metrics', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update a health metric
 */
export async function updateHealthMetric(date: string, data: HealthMetricFormType): Promise<HealthMetric> {
  return fetchAPI<HealthMetric>(`/api/v1/health/metrics/${date}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a health metric
 */
export async function deleteHealthMetric(date: string): Promise<void> {
  return fetchAPI<void>(`/api/v1/health/metrics/${date}`, {
    method: 'DELETE',
  });
}

// ============ Dashboard Endpoints ============

/**
 * Get today's overview metrics
 */
export async function getOverview(targetDate?: string): Promise<OverviewResponse> {
  const params = targetDate ? `?target_date=${targetDate}` : '';
  return fetchAPI<OverviewResponse>(`/api/v1/dashboard/overview${params}`);
}

/**
 * Get trend data for specified number of days
 */
export async function getTrends(days: number = 30, endDate?: string): Promise<TrendResponse> {
  const params = new URLSearchParams({ days: days.toString() });
  if (endDate) {
    params.append('end_date', endDate);
  }
  return fetchAPI<TrendResponse>(`/api/v1/dashboard/trends?${params}`);
}

/**
 * Get dashboard summary for current user
 */
export async function getDashboardSummary(targetDate?: string): Promise<SummaryResponse> {
  const params = targetDate ? `?target_date=${targetDate}` : '';
  return fetchAPI<SummaryResponse>(`/api/v1/dashboard/summary${params}`);
}

// ============ Garmin Endpoints ============

/**
 * Connect to Garmin with username/password
 */
export async function connectGarmin(
  username: string,
  password: string,
  mfaToken?: string,
  isCn: boolean = false
): Promise<GarminConnection> {
  const body: GarminLoginRequest = { username, password, is_cn: isCn };
  if (mfaToken) {
    body.mfa_token = mfaToken;
  }
  return fetchAPI<GarminConnection>('/api/v1/garmin/connect', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Get Garmin connection status
 */
export async function getGarminConnection(): Promise<GarminConnection> {
  return fetchAPI<GarminConnection>('/api/v1/garmin/connection');
}

/**
 * Unlink Garmin account
 */
export async function unlinkGarmin(): Promise<{ message: string }> {
  return fetchAPI('/api/v1/garmin/connection', {
    method: 'DELETE',
  });
}

/**
 * Trigger Garmin data sync
 */
export async function syncGarmin(days: number = 7, startDate?: string): Promise<GarminSyncResponse> {
  const body: { days?: number; start_date?: string } = { days };
  if (startDate) {
    body.start_date = startDate;
  }
  return fetchAPI<GarminSyncResponse>('/api/v1/garmin/sync', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ============ Strava Endpoints ============

/**
 * Get Strava app config status
 */
export async function getStravaConfig(): Promise<{ has_config: boolean }> {
  return fetchAPI('/api/v1/strava/config');
}

/**
 * Save Strava app credentials
 */
export async function saveStravaConfig(clientId: string, clientSecret: string): Promise<{ message: string }> {
  return fetchAPI('/api/v1/strava/config', {
    method: 'POST',
    body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
  });
}

/**
 * Get Strava authorization URL
 */
export async function getStravaAuthUrl(redirectUri?: string): Promise<{ authorization_url: string }> {
  const params = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : '';
  return fetchAPI(`/api/v1/strava/authorize${params}`);
}

/**
 * Handle Strava OAuth callback
 */
export async function stravaCallback(code: string): Promise<StravaConnection> {
  return fetchAPI<StravaConnection>('/api/v1/strava/callback', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

/**
 * Get Strava connection status
 */
export async function getStravaConnection(): Promise<StravaConnection> {
  return fetchAPI<StravaConnection>('/api/v1/strava/connection');
}

/**
 * Unlink Strava account
 */
export async function unlinkStrava(): Promise<{ message: string }> {
  return fetchAPI('/api/v1/strava/connection', {
    method: 'DELETE',
  });
}

/**
 * Trigger Strava data sync
 */
export async function syncStrava(days: number = 30, afterDate?: string): Promise<StravaSyncResponse> {
  const body: { days?: number; after_date?: string } = { days };
  if (afterDate) {
    body.after_date = afterDate;
  }
  return fetchAPI<StravaSyncResponse>('/api/v1/strava/sync', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Get Strava activities
 */
export async function getStravaActivities(
  startDate?: string,
  endDate?: string,
  limit: number = 50,
  activityType?: string
): Promise<StravaActivitiesResponse> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  params.append('limit', limit.toString());
  if (activityType) params.append('activity_type', activityType);

  const endpoint = `/api/v1/strava/activities${params.toString() ? `?${params}` : ''}`;
  return fetchAPI<StravaActivitiesResponse>(endpoint);
}

/**
 * Get a single Strava activity
 */
export async function getStravaActivity(activityId: number): Promise<StravaActivity> {
  return fetchAPI<StravaActivity>(`/api/v1/strava/activities/${activityId}`);
}

// ============ Preferences Endpoints ============

/**
 * Get current user's preferences
 */
export async function getUserPreferences(): Promise<UserPreference> {
  return fetchAPI<UserPreference>('/api/v1/preferences');
}

/**
 * Update user preferences
 */
export async function updateUserPreferences(preferences: UserPreferenceUpdateType): Promise<UserPreference> {
  return fetchAPI<UserPreference>('/api/v1/preferences', {
    method: 'PUT',
    body: JSON.stringify(preferences),
  });
}

/**
 * Update hidden cards preference
 */
export async function updateHiddenCards(hiddenCards: string): Promise<{ message: string; hidden_cards: string | null }> {
  return fetchAPI('/api/v1/preferences/hidden-cards', {
    method: 'PUT',
    body: JSON.stringify({ hidden_cards: hiddenCards }),
  });
}
