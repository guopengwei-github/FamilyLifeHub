# ABOUTME: Garmin Connect service for OAuth authentication and health data sync
# ABOUTME: Handles username/password login, MFA flow, token persistence, and data ingestion
import garth
from garth.http import Client
from garth.sso import login as garth_login, resume_login
from garth.exc import GarthHTTPError, GarthException
from garth.stats import DailySteps, DailyIntensityMinutes, DailyHRV, DailyStress
from garth import DailyBodyBatteryStress
from datetime import datetime, timedelta, date, timezone
from typing import Dict, List, Optional, Any, Tuple
import logging
import secrets
import base64
import pickle
import traceback

from app.core.security import encrypt_token, decrypt_token
from app.models import User, GarminConnection, HealthMetric, GarminActivity, BodyStatusTimeseries
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Server-side session storage for MFA flow
# Maps session_id -> {"client": Client, "signin_params": dict, "created_at": datetime}
# LIMITATION: In-memory storage means MFA sessions are lost on server restart.
# Users in the middle of MFA verification will need to restart the flow.
# For production, consider using Redis or another persistent cache.
_mfa_sessions: Dict[str, Dict[str, Any]] = {}

# Session timeout for MFA (10 minutes)
_MFA_SESSION_TIMEOUT = timedelta(minutes=10)


def cleanup_expired_mfa_sessions():
    """Remove expired MFA sessions from the in-memory store."""
    now = datetime.now(timezone.utc)
    expired_sessions = [
        session_id
        for session_id, session_data in _mfa_sessions.items()
        if now - session_data.get("created_at", now) > _MFA_SESSION_TIMEOUT
    ]
    for session_id in expired_sessions:
        del _mfa_sessions[session_id]
        logger.debug(f"Cleaned up expired MFA session: {session_id}")


def store_mfa_session(client: Client, signin_params: dict, is_cn: bool = False, username: str = "", password: str = "") -> str:
    """
    Store Client object and signin params for MFA resume.

    Args:
        client: The garth Client with pending MFA session
        signin_params: Signin parameters from garth_login
        is_cn: True for China (garmin.cn), False for International (garmin.com)
        username: Garmin username (for saving connection after MFA)
        password: Garmin password (for saving connection after MFA)

    Returns:
        Session ID for retrieving this session later
    """
    cleanup_expired_mfa_sessions()

    session_id = secrets.token_urlsafe(32)
    _mfa_sessions[session_id] = {
        "client": client,
        "signin_params": signin_params,
        "is_cn": is_cn,
        "username": username,
        "password": password,
        "created_at": datetime.now(timezone.utc)
    }
    logger.info(f"Stored MFA session: {session_id[:16]}...")
    return session_id


def get_mfa_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored MFA session data.

    Args:
        session_id: The session ID returned by store_mfa_session

    Returns:
        Dict with "client" and "signin_params", or None if session expired/not found
    """
    cleanup_expired_mfa_sessions()

    session_data = _mfa_sessions.get(session_id)
    if not session_data:
        logger.warning(f"MFA session not found or expired: {session_id[:16] if session_id else 'empty'}...")
        return None

    logger.info(f"Retrieved MFA session: {session_id[:16]}...")
    return session_data


def delete_mfa_session(session_id: str):
    """Remove an MFA session from storage."""
    if session_id in _mfa_sessions:
        del _mfa_sessions[session_id]
        logger.debug(f"Deleted MFA session: {session_id[:16]}...")


class GarminServiceError(Exception):
    """Base exception for Garmin service errors."""
    pass


class GarminAuthError(GarminServiceError):
    """Exception for Garmin authentication errors."""
    pass


class GarminAPIError(GarminServiceError):
    """Exception for Garmin API errors."""
    pass


def serialize_oauth_tokens(client: Client) -> str:
    """
    Serialize the garth client's OAuth tokens to a base64 encoded string.

    Args:
        client: Authenticated garth Client instance

    Returns:
        Base64 encoded string containing the serialized tokens, or empty string on failure
    """
    try:
        if not client.oauth1_token:
            logger.warning("No OAuth1 token found on client!")
            return ""
        if not client.oauth2_token:
            logger.warning("No OAuth2 token found on client!")
            return ""

        token_data = client.dumps()
        logger.info(f"Serialized OAuth tokens: {len(token_data)} chars")
        return base64.b64encode(token_data.encode('utf-8')).decode('utf-8')

    except Exception as e:
        logger.error(f"Failed to serialize OAuth tokens: {e}")
        logger.debug(f"Full traceback:", exc_info=True)
        return ""


def deserialize_oauth_tokens(token_str: str, client: Client) -> bool:
    """
    Deserialize OAuth tokens from a base64 encoded string and load into client.

    Args:
        token_str: Base64 encoded string containing serialized tokens
        client: The garth Client to load tokens into

    Returns:
        True if tokens were successfully loaded, False otherwise
    """
    try:
        token_data = base64.b64decode(token_str.encode('utf-8')).decode('utf-8')
        client.loads(token_data)
        logger.debug("Successfully deserialized OAuth tokens")
        return True

    except Exception as e:
        logger.warning(f"Failed to deserialize OAuth tokens: {e}")
        logger.debug(f"Full traceback:", exc_info=True)
        return False


def login(
    username: str,
    password: str,
    mfa_token: Optional[str] = None,
    is_cn: bool = False,
    mfa_session_id: Optional[str] = None
) -> Tuple[Client, dict]:
    """
    Login to Garmin Connect using garth library.

    Args:
        username: Garmin Connect username (email)
        password: Garmin Connect password
        mfa_token: Optional MFA token if Garmin requires 2FA
        is_cn: True for China (garmin.cn), False for International (garmin.com)
        mfa_session_id: Optional MFA session ID from previous MFA detection

    Returns:
        Tuple of (authenticated Client, user_info dict)

    Raises:
        GarminAuthError: If login fails

    Flow:
    1. Initial call (no mfa_token, no mfa_session_id): Attempts login with return_on_mfa=True
       - If MFA required: raises GarminAuthError with MFA_REQUIRED:<session_id> message
       - If no MFA: returns authenticated Client
    2. MFA call (with mfa_token and mfa_session_id): Completes login using resume_login()
       - Retrieves Client from server-side session storage
       - Calls resume_login with the same Client object
    """
    region = "Garmin China" if is_cn else "Garmin International"
    logger.info(f"Attempting {region} login for user: {username[:3]}***")

    client = None

    # If MFA token is provided with session_id, complete the login
    if mfa_token and mfa_session_id:
        logger.info(f"Completing {region} MFA login with session: {mfa_session_id[:16]}...")

        # Retrieve the stored session with Client object
        session_data = get_mfa_session(mfa_session_id)
        if not session_data:
            raise GarminAuthError(
                "MFA session expired or not found. "
                "Please start the login process again."
            )

        try:
            client = session_data["client"]
            signin_params = session_data["signin_params"]

            # Reconstruct the client_state for resume_login
            # This uses the SAME Client object that was used in the first request
            client_state = {
                "client": client,
                "signin_params": signin_params
            }

            logger.info(f"Calling resume_login with MFA code...")
            oauth1, oauth2 = resume_login(client_state, mfa_token)

            # Set tokens to our client
            client.oauth1_token = oauth1
            client.oauth2_token = oauth2
            logger.info(f"Successfully authenticated with {region} using MFA")

            # Clean up the session after successful login
            delete_mfa_session(mfa_session_id)

            # Skip the initial login attempt below - we're already authenticated
            # Continue to fetch user profile
            logger.info("MFA completed successfully, proceeding to fetch user profile")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"MFA login failed: {e}")

            if "ticket" in error_msg.lower():
                raise GarminAuthError(
                    "MFA verification failed. The code may have expired. "
                    "Please request a new verification code and try again."
                )
            if "invalid" in error_msg.lower() or "incorrect" in error_msg.lower():
                raise GarminAuthError(
                    "Invalid verification code. Please check the code and try again."
                )
            raise GarminAuthError(f"MFA verification failed: {error_msg}")

    # Initial login attempt - only runs when NOT completing MFA
    # This prevents creating a new Client and triggering a second login during MFA flow
    if client is None:
        logger.info(f"Attempting {region} login (with return_on_mfa=True)")

        # Create and configure client
        client = Client()
        if is_cn:
            client.configure(domain="garmin.cn")

        try:
            logger.info(f"Calling garth_login with username={username[:3]}***, return_on_mfa=True")
            result = garth_login(username, password, client=client, return_on_mfa=True)

        except GarthException as e:
            # garth throws "Unexpected title" when it encounters MFA pages
            # that don't have "MFA" in the title (e.g., "GARMIN Authentication Application")
            error_msg = str(e)
            logger.info(f"GarthException caught: {error_msg[:100]}")
            if "Unexpected title" in error_msg:
                title = error_msg.replace("Unexpected title: ", "").strip()
                logger.info(f"Unexpected title detected: {title}")
                # Check if this is an MFA/Authentication page
                if "authentication" in title.lower() or "mfa" in title.lower():
                    logger.info(f"MFA detected via Unexpected title: {title}")
                    # Store the client session for MFA resume
                    # We need to create signin_params manually since garth didn't return them
                    signin_params = {
                        "id": "gauth-widget",
                        "embedWidget": "true",
                        "gauthHost": f"https://sso.{'garmin.cn' if is_cn else 'garmin.com'}/sso",
                    }
                    session_id = store_mfa_session(client, signin_params, is_cn, username, password)
                    logger.info(f"MFA session created: {session_id[:16]}...")
                    # Raise this OUTSIDE the try-except so it doesn't get caught
                    raise GarminAuthError(f"MFA_REQUIRED:{session_id}")
            # Not an MFA-related Unexpected title, re-raise
            raise
        except Exception as e:
            # Other exceptions from garth_login
            error_msg = str(e)
            logger.error(f"{region} login failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message details: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Check if this is our MFA_REQUIRED error with session_id - MUST BE FIRST!
            if error_msg.startswith("MFA_REQUIRED:"):
                # Pass through the MFA_REQUIRED error with session_id intact
                raise

            # Check for other MFA-related errors (but not our MFA_REQUIRED)
            mfa_keywords = [
                "MFA session storage failed",  # Our storage error
                "MFA verification failed",
                "MFA session expired"
            ]
            if any(keyword.lower() in error_msg.lower() for keyword in mfa_keywords):
                # These are actual errors, re-raise as-is
                raise

            # Check for MFA requirement without session_id
            mfa_indicators = [
                "2FA", "OTP", "authenticator",
                "verification code", "verify your identity",
                "ticket", "mfa", "otp"
            ]
            if any(keyword.lower() in error_msg.lower() for keyword in mfa_indicators):
                logger.info(f"MFA detected in error message, requiring MFA verification")
                raise GarminAuthError("MFA_REQUIRED")

            # Now check for actual invalid credentials (but not MFA-related)
            if "401" in error_msg or "Unauthorized" in error_msg:
                logger.info(f"Login failed with 401/Unauthorized - invalid credentials")
                raise GarminAuthError("Invalid credentials")
            raise GarminAuthError(f"Login failed: {error_msg}")

        # If we get here, garth_login succeeded without MFA
        logger.info(f"garth_login returned: {type(result)}, is_tuple: {isinstance(result, tuple)}")
        if isinstance(result, tuple):
            logger.info(f"Result length: {len(result)}, first element: {result[0] if len(result) > 0 else 'N/A'}")

        # Check if MFA is required (normal flow via garth)
        if isinstance(result, tuple) and len(result) == 2 and result[0] == "needs_mfa":
            logger.info("MFA is required for this account")
            # result[1] is the client_state dict containing 'client' and 'signin_params'
            client_state_dict = result[1]
            signin_params = client_state_dict.get("signin_params", {})
            logger.info(f"Client state keys: {list(client_state_dict.keys())}")

            # Store the Client object in server-side session storage
            # This preserves the session context for resume_login
            session_id = store_mfa_session(client, signin_params, is_cn, username, password)
            # Return the session ID to the frontend
            logger.info(f"MFA session created for normal flow: {session_id[:16]}...")
            raise GarminAuthError(f"MFA_REQUIRED:{session_id}")

        # No MFA required - result contains (OAuth1Token, OAuth2Token)
        oauth1, oauth2 = result
        client.oauth1_token = oauth1
        client.oauth2_token = oauth2
        logger.info(f"Successfully authenticated with {region}")

    # Fetch user profile
    try:
        profile = client.connectapi("/userprofile-service/socialProfile")
        user_info = {
            'garmin_user_id': str(profile.get('id')) if profile.get('id') else None,
            'garmin_display_name': profile.get('displayName'),
        }
        logger.info(f"User profile fetched: {user_info}")
    except Exception as e:
        logger.warning(f"Failed to fetch user profile: {e}")
        user_info = {'garmin_user_id': None, 'garmin_display_name': None}

    return client, user_info


def fetch_daily_summary(client: Client, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily wellness summary from Garmin.

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch summary for

    Returns:
        Daily summary data dictionary or None
    """
    try:
        date_str = target_date.strftime('%Y-%m-%d')

        # Get user_id from profile first
        profile = client.connectapi("/userprofile-service/socialProfile")
        if not profile:
            logger.error("Cannot get profile to find user ID")
            return None

        user_id = profile.get('id')
        if not user_id:
            logger.error("No user ID in profile")
            return None

        # Call the sleep data endpoint
        summary = client.connectapi(
            f"/wellness-service/wellness/dailySleepData/{user_id}?date={date_str}"
        )

        logger.info(f"Fetched daily summary for {date_str}")
        return summary

    except Exception as e:
        logger.warning(f"Error fetching daily summary for {target_date}: {e}")
        return None


def fetch_daily_wellness(client: Client, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily wellness summary (steps, distance, calories) from Garmin.

    Uses garth Stats API for steps/distance which works for both CN and International.
    Attempts to fetch calories from wellness summary endpoint (may not work for CN users).

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch wellness data for

    Returns:
        Daily wellness data dictionary or None
    """
    result = {}

    # Fetch steps and distance from Stats API
    try:
        steps_data = DailySteps.list(end=target_date, period=1, client=client)
        logger.debug(f"DailySteps.list() returned {len(steps_data)} items for {target_date}")
        if steps_data:
            data = steps_data[0]
            result['totalSteps'] = data.total_steps
            result['totalDistanceMeters'] = data.total_distance
            logger.debug(f"Steps data for {target_date}: steps={data.total_steps}, distance={data.total_distance}m")
    except Exception as e:
        logger.warning(f"Error fetching daily steps for {target_date}: {e}")
        logger.debug(traceback.format_exc())

    # Try to fetch calories from wellness summary endpoint
    # Note: This may not work for CN users (returns 405)
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        profile = client.connectapi("/userprofile-service/socialProfile")
        if profile and profile.get('id'):
            user_id = profile['id']
            wellness_summary = client.connectapi(
                f"/wellness-service/wellness/dailySummary/{user_id}?date={date_str}"
            )
            if wellness_summary:
                # Extract calories from various possible fields
                if 'totalKilocalories' in wellness_summary:
                    result['totalKilocalories'] = wellness_summary['totalKilocalories']
                    logger.debug(f"Calories from totalKilocalories: {wellness_summary['totalKilocalories']}")
                elif 'kilocalories' in wellness_summary:
                    result['totalKilocalories'] = wellness_summary['kilocalories']
                    logger.debug(f"Calories from kilocalories: {wellness_summary['kilocalories']}")
                elif 'activeKilocalories' in wellness_summary:
                    result['totalKilocalories'] = wellness_summary['activeKilocalories']
                    logger.debug(f"Calories from activeKilocalories: {wellness_summary['activeKilocalories']}")
    except Exception as e:
        logger.debug(f"Could not fetch calories from wellness summary (expected for CN users): {e}")

    return result if result else None


def fetch_daily_intensity(client: Client, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily intensity minutes (exercise duration) from Garmin using garth Stats API.

    Note: This uses the DailyIntensityMinutes stats which works for both CN and International.

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch intensity data for

    Returns:
        Dictionary with moderate and vigorous intensity minutes
    """
    try:
        intensity_data = DailyIntensityMinutes.list(end=target_date, period=1, client=client)
        logger.debug(f"DailyIntensityMinutes.list() returned {len(intensity_data)} items for {target_date}")
        if intensity_data:
            data = intensity_data[0]
            total_minutes = (data.moderate_value or 0) + (data.vigorous_value or 0)
            logger.debug(f"Intensity data for {target_date}: moderate={data.moderate_value}, vigorous={data.vigorous_value}, total={total_minutes}")
            return {
                'moderate_minutes': data.moderate_value,
                'vigorous_minutes': data.vigorous_value,
                'total_minutes': total_minutes,
            }
        logger.warning(f"DailyIntensityMinutes.list() returned empty or None data for {target_date}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching daily intensity for {target_date}: {e}")
        logger.debug(traceback.format_exc())
        return None


def fetch_daily_body_battery(client: Client, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily body battery data from Garmin using garth Stats API.

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch body battery data for

    Returns:
        Dictionary with current_body_battery, min, max values or None
    """
    try:
        bb_data = DailyBodyBatteryStress.list(end=target_date, days=1, client=client)
        logger.debug(f"DailyBodyBatteryStress.list() returned {len(bb_data)} items for {target_date}")
        if bb_data:
            data = bb_data[0]
            result = {
                'current_body_battery': data.current_body_battery,
                'min_body_battery': data.min_body_battery,
                'max_body_battery': data.max_body_battery,
            }
            logger.debug(f"Body battery for {target_date}: current={data.current_body_battery}")
            return result
        return None
    except Exception as e:
        logger.warning(f"Error fetching daily body battery for {target_date}: {e}")
        logger.debug(traceback.format_exc())
        return None


def fetch_daily_stress(client: Client, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily stress level data from Garmin using garth Stats API.

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch stress data for

    Returns:
        Dictionary with overall_stress_level or None
    """
    try:
        stress_data = DailyStress.list(period=1, client=client)
        logger.debug(f"DailyStress.list() returned {len(stress_data)} items for {target_date}")
        if stress_data:
            data = stress_data[0]
            result = {
                'overall_stress_level': data.overall_stress_level,
            }
            logger.debug(f"Stress for {target_date}: overall={data.overall_stress_level}")
            return result
        return None
    except Exception as e:
        logger.warning(f"Error fetching daily stress for {target_date}: {e}")
        logger.debug(traceback.format_exc())
        return None


def fetch_daily_steps(client: Client, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily steps data from Garmin using garth Stats API.

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch steps data for

    Returns:
        Dictionary with total_steps, total_distance or None
    """
    try:
        steps_data = DailySteps.list(period=1, client=client)
        logger.debug(f"DailySteps.list(period=1) returned {len(steps_data)} items")
        if steps_data:
            data = steps_data[0]
            result = {
                'total_steps': data.total_steps,
                'total_distance': data.total_distance,
            }
            logger.debug(f"Steps for {target_date}: steps={data.total_steps}, distance={data.total_distance}m")
            return result
        return None
    except Exception as e:
        logger.warning(f"Error fetching daily steps for {target_date}: {e}")
        logger.debug(traceback.format_exc())
        return None


def fetch_daily_hrv(client: Client, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily HRV (Heart Rate Variability) data from Garmin using garth Stats API.

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch HRV data for

    Returns:
        Dictionary with last_night_avg, weekly_avg, status or None
    """
    try:
        hrv_data = DailyHRV.list(period=1, client=client)
        logger.debug(f"DailyHRV.list(period=1) returned {len(hrv_data)} items")
        if hrv_data:
            data = hrv_data[0]
            result = {
                'last_night_avg': data.last_night_avg,
                'weekly_avg': data.weekly_avg,
                'status': data.status,
            }
            logger.debug(f"HRV for {target_date}: last_night={data.last_night_avg}, weekly={data.weekly_avg}, status={data.status}")
            return result
        return None
    except Exception as e:
        logger.warning(f"Error fetching daily HRV for {target_date}: {e}")
        logger.debug(traceback.format_exc())
        return None


def fetch_daily_activities(client: Client, target_date: date) -> List[Dict[str, Any]]:
    """
    Fetch activities for a specific date from Garmin.

    Args:
        client: Authenticated garth Client
        target_date: Date to fetch activities for

    Returns:
        List of activity dictionaries or empty list
    """
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        activities = client.connectapi(
            f"/activity-service/activity/list?startDate={date_str}&endDate={date_str}"
        )
        logger.debug(f"Activities for {date_str}: count={len(activities) if activities else 0}")
        return activities if activities else []
    except Exception as e:
        logger.warning(f"Error fetching activities for {target_date}: {e}")
        logger.debug(traceback.format_exc())
        return []


def parse_garmin_time(time_str: Optional[str]) -> Optional[datetime]:
    """
    Parse Garmin timestamp string to datetime object.

    Args:
        time_str: ISO format timestamp string from Garmin

    Returns:
        datetime object or None
    """
    if not time_str:
        return None
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int, returning None if conversion fails."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float, returning None if conversion fails."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def map_garmin_to_health_metric(
    user_id: int,
    garmin_data: Dict[str, Any],
    metric_date: date,
    wellness_data: Optional[Dict[str, Any]] = None,
    intensity_data: Optional[Dict[str, Any]] = None,
    body_battery_data: Optional[Dict[str, Any]] = None,
    stress_data: Optional[Dict[str, Any]] = None,
    steps_data: Optional[Dict[str, Any]] = None,
    hrv_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Map Garmin API data to HealthMetric fields.

    Args:
        user_id: User ID
        garmin_data: Garmin daily summary data from dailySleepData endpoint
        metric_date: Date for the metric
        wellness_data: Optional daily wellness data (steps, distance)
        intensity_data: Optional intensity data (exercise minutes)
        body_battery_data: Optional body battery data (current, min, max)
        stress_data: Optional daily stress data (overall_stress_level)
        steps_data: Optional daily steps data (total_steps, total_distance)
        hrv_data: Optional daily HRV data (last_night_avg, weekly_avg, status)

    Returns:
        Dictionary with HealthMetric fields
    """
    metric = {
        'user_id': user_id,
        'date': metric_date,
        'sleep_hours': None,
        'light_sleep_hours': None,
        'deep_sleep_hours': None,
        'rem_sleep_hours': None,
        'resting_heart_rate': None,
        'stress_level': None,
        'exercise_minutes': None,
        'steps': None,
        'calories': None,
        'distance_km': None,
        'body_battery': None,
        'spo2': None,
        'respiration_rate': None,
        'resting_hr': None,
        'sleep_score': None,
        'hrv_last_night': None,
        'hrv_weekly_avg': None,
        'hrv_status': None,
    }

    # Extract data from dailySleepDTO structure
    if 'dailySleepDTO' in garmin_data:
        dto = garmin_data.get('dailySleepDTO', {})
        if dto:
            if dto.get('sleepTimeSeconds'):
                metric['sleep_hours'] = dto['sleepTimeSeconds'] / 3600
            if dto.get('deepSleepSeconds'):
                metric['deep_sleep_hours'] = dto['deepSleepSeconds'] / 3600
            if dto.get('lightSleepSeconds'):
                metric['light_sleep_hours'] = dto['lightSleepSeconds'] / 3600
            if dto.get('remSleepSeconds'):
                metric['rem_sleep_hours'] = dto['remSleepSeconds'] / 3600
            if dto.get('sleepScores'):
                scores = dto.get('sleepScores', {})
                if isinstance(scores, dict) and 'overall' in scores:
                    overall = scores['overall']
                    if isinstance(overall, dict) and 'value' in overall:
                        metric['sleep_score'] = _safe_int(overall['value'])
                    elif isinstance(overall, int):
                        metric['sleep_score'] = overall

    # Extract resting heart rate
    if 'restingHeartRate' in garmin_data and garmin_data['restingHeartRate']:
        metric['resting_hr'] = _safe_int(garmin_data['restingHeartRate'])
        metric['resting_heart_rate'] = metric['resting_hr']

    # Extract stress from sleepStress array
    if 'sleepStress' in garmin_data and garmin_data['sleepStress']:
        stress_values = [s.get('value') for s in garmin_data['sleepStress'] if s.get('value') is not None]
        if stress_values:
            metric['stress_level'] = _safe_int(sum(stress_values) / len(stress_values))

    # Extract body battery - prefer real-time data over sleep data
    if body_battery_data and body_battery_data.get('current_body_battery') is not None:
        metric['body_battery'] = _safe_int(body_battery_data['current_body_battery'])
        logger.debug(f"    Using real-time body_battery: {metric['body_battery']}")
    elif 'sleepBodyBattery' in garmin_data and garmin_data['sleepBodyBattery']:
        bb_values = [b.get('value') for b in garmin_data['sleepBodyBattery'] if b.get('value') is not None]
        if bb_values:
            metric['body_battery'] = _safe_int(bb_values[-1])
            logger.debug(f"    Using sleep body_battery (fallback): {metric['body_battery']}")

    # Extract SpO2 (case-insensitive key lookup)
    spo2_key = next((k for k in garmin_data.keys() if 'spo2sleepsummarydto' in k.lower()), None)
    if spo2_key:
        spo2_data = garmin_data[spo2_key]
        # Case-insensitive check for avgSpO2 key - try both 'averageSpO2' and 'avgSpO2'
        avg_spo2_key = next((k for k in spo2_data.keys() if k.lower() in ('avgspo2', 'averagespo2')), None)
        if avg_spo2_key:
            metric['spo2'] = _safe_float(spo2_data[avg_spo2_key])
            logger.debug(f"    Mapping SpO2: {spo2_data[avg_spo2_key]}% -> {metric['spo2']}")

    # Extract respiration (case-insensitive key lookup)
    # Try both 'wellnessEpochRespirationDataDTOList' and 'respirationAveragesList'
    respiration_key = next((k for k in garmin_data.keys() if 'respiration' in k.lower() and ('dto' in k.lower() or 'list' in k.lower() or 'average' in k.lower())), None)
    if respiration_key:
        resp_list = garmin_data[respiration_key]
        # Check for respirationValue key (new API) or breathsPerMinute key (old API)
        resp_values = []
        for r in resp_list:
            # Try 'respirationValue' first (new Garmin API format)
            if 'respirationValue' in r:
                if r['respirationValue'] is not None:
                    resp_values.append(r['respirationValue'])
            else:
                # Fallback to old 'breathsPerMinute' format
                bpm_key = next((k for k in r.keys() if k.lower() == 'breathsperminute'), None)
                if bpm_key and r[bpm_key] is not None:
                    resp_values.append(r[bpm_key])
        if resp_values:
            metric['respiration_rate'] = _safe_float(sum(resp_values) / len(resp_values))
            logger.debug(f"    Mapping respiration_rate: {metric['respiration_rate']} bpm (from {len(resp_values)} readings)")

    # Extract activity data from wellness summary (steps, distance, calories)
    if wellness_data:
        if 'totalSteps' in wellness_data:
            metric['steps'] = _safe_int(wellness_data['totalSteps'])
            logger.debug(f"    Mapping steps: {wellness_data['totalSteps']} -> {metric['steps']}")
        if 'totalDistanceMeters' in wellness_data:
            metric['distance_km'] = _safe_float(wellness_data['totalDistanceMeters'] / 1000)
            logger.debug(f"    Mapping distance: {wellness_data['totalDistanceMeters']}m -> {metric['distance_km']}km")
        if 'totalKilocalories' in wellness_data:
            metric['calories'] = _safe_int(wellness_data['totalKilocalories'])
            logger.debug(f"    Mapping calories: {wellness_data['totalKilocalories']} -> {metric['calories']}")

    # Extract exercise minutes from intensity data
    if intensity_data and 'total_minutes' in intensity_data:
        metric['exercise_minutes'] = _safe_int(intensity_data['total_minutes'])
        logger.debug(f"    Mapping exercise_minutes: {intensity_data['total_minutes']} -> {metric['exercise_minutes']}")

    # Extract stress level from daily stress data - prefer real-time data over sleep stress
    if stress_data and stress_data.get('overall_stress_level') is not None:
        metric['stress_level'] = _safe_int(stress_data['overall_stress_level'])
        logger.debug(f"    Using real-time stress_level: {metric['stress_level']}")

    # Extract steps from daily steps data - prefer real-time data over wellness data
    if steps_data and steps_data.get('total_steps') is not None:
        metric['steps'] = _safe_int(steps_data['total_steps'])
        logger.debug(f"    Using real-time steps: {metric['steps']}")

    # Extract HRV data
    if hrv_data:
        if hrv_data.get('last_night_avg') is not None:
            metric['hrv_last_night'] = _safe_int(hrv_data['last_night_avg'])
            logger.debug(f"    Mapping hrv_last_night: {hrv_data['last_night_avg']} -> {metric['hrv_last_night']}")
        if hrv_data.get('weekly_avg') is not None:
            metric['hrv_weekly_avg'] = _safe_int(hrv_data['weekly_avg'])
            logger.debug(f"    Mapping hrv_weekly_avg: {hrv_data['weekly_avg']} -> {metric['hrv_weekly_avg']}")
        if hrv_data.get('status') is not None:
            metric['hrv_status'] = hrv_data['status']
            logger.debug(f"    Mapping hrv_status: {hrv_data['status']} -> {metric['hrv_status']}")

    return metric


def save_garmin_activities(
    user_id: int,
    activities: List[Dict[str, Any]],
    activity_date: date,
    db_session
) -> int:
    """
    Save detailed Garmin activities to database.

    Args:
        user_id: User ID
        activities: List of activity data from Garmin
        activity_date: Date of the activities
        db_session: Database session

    Returns:
        Number of activities saved
    """
    count = 0
    for activity in activities:
        garmin_activity_id = activity.get('activityId')

        # Skip if no activity ID
        if not garmin_activity_id:
            continue

        # Check if activity already exists
        existing = db_session.query(GarminActivity).filter(
            GarminActivity.user_id == user_id,
            GarminActivity.garmin_activity_id == garmin_activity_id
        ).first()

        if existing:
            continue

        activity_type_info = activity.get('activityType', {})
        new_activity = GarminActivity(
            user_id=user_id,
            date=activity_date,
            garmin_activity_id=garmin_activity_id,
            activity_type=activity_type_info.get('typeKey'),
            activity_type_key=activity_type_info.get('typeKey'),
            name=activity.get('activityName'),
            duration_seconds=activity.get('duration'),
            distance_meters=activity.get('distance'),
            calories=activity.get('calories'),
            average_heartrate=activity.get('averageHR'),
            max_heartrate=activity.get('maxHR'),
            avg_speed_mps=activity.get('averageSpeed'),
            max_speed_mps=activity.get('maxSpeed'),
            elevation_gain_meters=activity.get('elevationGain'),
            start_time=parse_garmin_time(activity.get('startTimeGMT')),
            start_time_local=parse_garmin_time(activity.get('startTimeLocal')),
        )
        db_session.add(new_activity)
        count += 1

    return count


def save_body_status_timeseries(
    user_id: int,
    garmin_data: Dict[str, Any],
    target_date: date,
    db_session
) -> int:
    """
    Save body status timeseries data (body battery, stress, heart rate) to database.

    Args:
        user_id: User ID
        garmin_data: Raw Garmin daily summary data containing sleepBodyBattery and sleepStress arrays
        target_date: Date of the data
        db_session: Database session

    Returns:
        Number of timeseries records saved
    """
    count = 0
    timestamps_seen = set()

    # Delete existing timeseries data for this user and date
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date + timedelta(days=1), datetime.min.time())
    db_session.query(BodyStatusTimeseries).filter(
        BodyStatusTimeseries.user_id == user_id,
        BodyStatusTimeseries.timestamp >= start_dt,
        BodyStatusTimeseries.timestamp < end_dt
    ).delete()

    # Collect all data points by timestamp
    data_by_timestamp: Dict[datetime, Dict[str, Any]] = {}

    # Process sleepBodyBattery array
    if 'sleepBodyBattery' in garmin_data and garmin_data['sleepBodyBattery']:
        for item in garmin_data['sleepBodyBattery']:
            ts_millis = item.get('startTimestampGMT')
            value = item.get('value')
            if ts_millis is not None and value is not None:
                ts = datetime.utcfromtimestamp(ts_millis / 1000)
                if ts not in data_by_timestamp:
                    data_by_timestamp[ts] = {}
                data_by_timestamp[ts]['body_battery'] = _safe_int(value)

    # Process sleepStress array
    if 'sleepStress' in garmin_data and garmin_data['sleepStress']:
        for item in garmin_data['sleepStress']:
            ts_millis = item.get('startTimestampGMT')
            value = item.get('value')
            if ts_millis is not None and value is not None:
                ts = datetime.utcfromtimestamp(ts_millis / 1000)
                if ts not in data_by_timestamp:
                    data_by_timestamp[ts] = {}
                data_by_timestamp[ts]['stress_level'] = _safe_int(value)

    # Create records for each timestamp
    for ts, values in data_by_timestamp.items():
        record = BodyStatusTimeseries(
            user_id=user_id,
            timestamp=ts,
            body_battery=values.get('body_battery'),
            stress_level=values.get('stress_level'),
            heart_rate=values.get('heart_rate')
        )
        db_session.add(record)
        count += 1

    logger.debug(f"Saved {count} body status timeseries records for {target_date}")
    return count


def refresh_garmin_data(
    user_id: int,
    days: int = 7,
    db_session=None
) -> Dict[str, Any]:
    """
    Fetch and sync Garmin health metrics for a user.

    Args:
        user_id: User ID
        days: Number of days to sync (default: 7)
        db_session: Optional database session (creates new if not provided)

    Returns:
        Dictionary with sync results (success, count, errors)
    """
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        # Get user's Garmin connection
        connection = db.query(GarminConnection).filter(
            GarminConnection.user_id == user_id
        ).first()

        if not connection:
            raise GarminAuthError("No Garmin connection found for user")

        if connection.sync_status != "connected":
            raise GarminAuthError(f"Garmin connection not active: {connection.sync_status}")

        # Decrypt credentials
        username = decrypt_token(connection.garmin_username)
        password = decrypt_token(connection.garmin_password)
        is_cn = connection.is_cn == 1

        if not username or not password:
            raise GarminAuthError("Invalid stored credentials")

        # Try to use OAuth tokens first
        client = Client()
        if is_cn:
            client.configure(domain="garmin.cn")

        tokens_used = False

        if connection.garmin_oauth_tokens:
            try:
                token_str = decrypt_token(connection.garmin_oauth_tokens)
                if token_str and len(token_str) > 50:
                    logger.info(f"Found stored OAuth tokens: {len(token_str)} chars")

                    if deserialize_oauth_tokens(token_str, client):
                        # Verify tokens by making an API call
                        try:
                            profile = client.connectapi("/userprofile-service/socialProfile")
                            if profile:
                                tokens_used = True
                                logger.info("Stored OAuth tokens verified and working")
                            else:
                                logger.warning("Token verification returned empty profile")
                        except Exception as verify_err:
                            logger.warning(f"Token verification failed: {verify_err}")
                            tokens_used = False
                    else:
                        logger.warning("Failed to deserialize OAuth tokens")
                        tokens_used = False
                else:
                    logger.warning("Stored OAuth tokens are empty or too short")
                    tokens_used = False
            except Exception as e:
                logger.warning(f"Failed to load OAuth tokens: {e}")
                tokens_used = False

        # Fall back to username/password login if tokens didn't work
        if not tokens_used:
            logger.info("No valid OAuth tokens, performing username/password login")
            try:
                client, user_info = login(username, password, is_cn=is_cn)

                # Serialize and store the OAuth tokens
                new_oauth_tokens = serialize_oauth_tokens(client)
                if new_oauth_tokens:
                    encrypted_tokens = encrypt_token(new_oauth_tokens)
                    connection.garmin_oauth_tokens = encrypted_tokens
                    db.commit()
                    logger.info("Stored new OAuth tokens after successful login")
            except Exception as e:
                connection.sync_status = "error"
                connection.last_error = str(e)
                db.commit()
                raise GarminAuthError(f"Authentication failed: {str(e)}")

        # Calculate date range and fetch data
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        sync_results = {
            'success': False,
            'days_synced': 0,
            'metrics_created': 0,
            'metrics_updated': 0,
            'activities_created': 0,
            'errors': []
        }

        current_date = start_date
        while current_date <= end_date:
            try:
                logger.info(f"Fetching data for {current_date}")

                daily_summary = fetch_daily_summary(client, current_date)
                daily_wellness = fetch_daily_wellness(client, current_date)
                daily_intensity = fetch_daily_intensity(client, current_date)
                daily_body_battery = fetch_daily_body_battery(client, current_date)
                daily_stress = fetch_daily_stress(client, current_date)
                daily_steps = fetch_daily_steps(client, current_date)
                daily_hrv = fetch_daily_hrv(client, current_date)

                if not daily_summary:
                    logger.warning(f"No daily_summary data for {current_date}, skipping")
                    current_date += timedelta(days=1)
                    continue

                metric_data = map_garmin_to_health_metric(
                    user_id, daily_summary, current_date, daily_wellness, daily_intensity, daily_body_battery,
                    daily_stress, daily_steps, daily_hrv
                )

                # Check if we have any data worth saving
                has_data = any(
                    v is not None
                    for k, v in metric_data.items()
                    if k not in ['user_id', 'date']
                )

                if has_data:
                    logger.info(f"Saving metric_data: {metric_data}")
                    existing_metric = db.query(HealthMetric).filter(
                        HealthMetric.user_id == user_id,
                        HealthMetric.date == current_date
                    ).first()

                    if existing_metric:
                        logger.info(f"Updating existing metric for {current_date}")
                        for field, value in metric_data.items():
                            if field not in ['user_id', 'date'] and value is not None:
                                setattr(existing_metric, field, value)
                        existing_metric.updated_at = datetime.now(timezone.utc)
                        sync_results['metrics_updated'] += 1
                    else:
                        logger.info(f"Creating new metric for {current_date}")
                        new_metric = HealthMetric(**metric_data)
                        db.add(new_metric)
                        sync_results['metrics_created'] += 1

                    sync_results['days_synced'] += 1

                # Save body status timeseries data (regardless of has_data)
                if daily_summary:
                    save_body_status_timeseries(user_id, daily_summary, current_date, db)

            except Exception as e:
                logger.error(f"Error processing data for {current_date}: {e}")
                sync_results['errors'].append(f"{current_date}: {str(e)}")

            current_date += timedelta(days=1)

        # Commit changes and update connection
        db.commit()
        connection.last_sync_at = datetime.now(timezone.utc)
        connection.sync_status = "connected"
        connection.last_error = None
        db.commit()

        sync_results['success'] = True
        sync_results['last_sync_at'] = datetime.now(timezone.utc)
        return sync_results

    finally:
        if close_session:
            db.close()


def save_garmin_connection(
    user_id: int,
    username: str,
    password: str,
    mfa_token: Optional[str] = None,
    garmin_user_id: Optional[str] = None,
    garmin_display_name: Optional[str] = None,
    is_cn: bool = False,
    client: Optional[Client] = None,
    db_session=None
) -> GarminConnection:
    """
    Save or update Garmin connection for a user.

    Args:
        user_id: User ID
        username: Garmin Connect username (email)
        password: Garmin Connect password
        mfa_token: Optional MFA token (not used, kept for compatibility)
        garmin_user_id: Optional Garmin user ID
        garmin_display_name: Optional Garmin display name
        is_cn: True for China (garmin.cn), False for International (garmin.com)
        client: Optional authenticated Client to extract OAuth tokens from
        db_session: Optional database session

    Returns:
        GarminConnection object
    """
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        # Encrypt credentials
        encrypted_username = encrypt_token(username) if username else None
        encrypted_password = encrypt_token(password) if password else None

        # Serialize OAuth tokens if client is provided
        encrypted_oauth_tokens = None
        if client:
            oauth_tokens = serialize_oauth_tokens(client)
            if oauth_tokens:
                encrypted_oauth_tokens = encrypt_token(oauth_tokens)
                logger.info("Successfully serialized and encrypted OAuth tokens")

        # Check for existing connection
        existing = db.query(GarminConnection).filter(
            GarminConnection.user_id == user_id
        ).first()

        if existing:
            # Update existing connection
            if encrypted_username:
                existing.garmin_username = encrypted_username
            if encrypted_password:
                existing.garmin_password = encrypted_password
            if encrypted_oauth_tokens:
                existing.garmin_oauth_tokens = encrypted_oauth_tokens
            existing.garmin_user_id = garmin_user_id or existing.garmin_user_id
            existing.garmin_display_name = garmin_display_name or existing.garmin_display_name
            existing.is_cn = 1 if is_cn else 0
            existing.updated_at = datetime.now(timezone.utc)
            existing.sync_status = "connected"
            existing.last_error = None
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # For new connections, require username/password
            if not encrypted_username or not encrypted_password:
                raise ValueError("Username and password are required for new Garmin connections")
            # Create new connection
            connection = GarminConnection(
                user_id=user_id,
                garmin_username=encrypted_username,
                garmin_password=encrypted_password,
                garmin_oauth_tokens=encrypted_oauth_tokens,
                garmin_mfa_token=None,
                garmin_user_id=garmin_user_id,
                garmin_display_name=garmin_display_name,
                is_cn=1 if is_cn else 0,
                sync_status="connected"
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)
            return connection

    finally:
        if close_session:
            db.close()


def resume_mfa_login(mfa_token: str, mfa_session_id: str) -> Tuple[Client, dict, bool, str, str]:
    """
    Complete MFA login (second step without credentials).

    This function is used after the initial login attempt has detected MFA
    requirement and stored the Client object in server-side session storage.

    Args:
        mfa_token: MFA verification code from email
        mfa_session_id: Session ID from initial login attempt

    Returns:
        Tuple of (authenticated Client, user_info dict, is_cn, username, password)

    Raises:
        GarminAuthError: If MFA verification fails or session expires
    """
    logger.info(f"Completing Garmin MFA login with session: {mfa_session_id[:16]}...")

    # Retrieve the stored session with Client object
    session_data = get_mfa_session(mfa_session_id)
    if not session_data:
        raise GarminAuthError(
            "MFA session expired or not found. "
            "Please start the login process again."
        )

    try:
        client = session_data["client"]
        signin_params = session_data["signin_params"]
        is_cn = session_data.get("is_cn", False)
        username = session_data.get("username", "")
        password = session_data.get("password", "")

        # Reconstruct the client_state for resume_login
        # This uses the SAME Client object that was used in the first request
        client_state = {
            "client": client,
            "signin_params": signin_params
        }

        logger.info(f"Calling resume_login with MFA code...")
        oauth1, oauth2 = resume_login(client_state, mfa_token)

        # Set tokens to our client
        client.oauth1_token = oauth1
        client.oauth2_token = oauth2
        logger.info(f"Successfully authenticated using MFA")

        # Clean up the session after successful login
        delete_mfa_session(mfa_session_id)

        # Fetch user profile
        try:
            profile = client.connectapi("/userprofile-service/socialProfile")
            user_info = {
                'garmin_user_id': str(profile.get('id')) if profile.get('id') else None,
                'garmin_display_name': profile.get('displayName'),
            }
            logger.info(f"User profile fetched: {user_info}")
        except Exception as e:
            logger.warning(f"Failed to fetch user profile: {e}")
            user_info = {'garmin_user_id': None, 'garmin_display_name': None}

        return client, user_info, is_cn, username, password

    except Exception as e:
        error_msg = str(e)
        logger.error(f"MFA login failed: {e}")

        if "ticket" in error_msg.lower():
            raise GarminAuthError(
                "MFA verification failed. The code may have expired. "
                "Please request a new verification code and try again."
            )
        if "invalid" in error_msg.lower() or "incorrect" in error_msg.lower():
            raise GarminAuthError(
                "Invalid verification code. Please check the code and try again."
            )
        raise GarminAuthError(f"MFA verification failed: {error_msg}")


def test_garmin_credentials(username: str, password: str, mfa_token: Optional[str] = None, is_cn: bool = False) -> bool:
    """
    Test if Garmin credentials are valid.

    Args:
        username: Garmin Connect username
        password: Garmin Connect password
        mfa_token: Optional MFA token
        is_cn: True for China (garmin.cn), False for International (garmin.com)

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        client, user_info = login(username, password, mfa_token, is_cn)
        return client is not None
    except Exception as e:
        logger.warning(f"Credentials test failed: {e}")
        return False
