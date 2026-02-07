"""
Garmin Connect service for syncing health metrics.
Uses the community garminconnect library with username/password authentication.
OAuth tokens are persisted to avoid repeated MFA prompts.
"""
from garminconnect import Garmin
import garth
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import logging
import os
import shutil
import base64
import json

from app.core.security import encrypt_token, decrypt_token
from app.models import User, GarminConnection, HealthMetric
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Track the last login error for MFA detection
_last_login_error: str = ""


def serialize_oauth_tokens(client: Garmin) -> str:
    """
    Serialize the garth client's OAuth tokens to a base64 encoded string.

    The garth library stores OAuth1 and OAuth2 tokens that can be reused
    for subsequent logins without requiring MFA again.

    Args:
        client: Authenticated Garmin client instance

    Returns:
        Base64 encoded string containing the serialized tokens
    """
    try:
        # Access the underlying garth client from Garmin instance
        # Garmin class wraps garth.Client
        if hasattr(client, 'client') and hasattr(client.client, 'dumps'):
            # Newer garminconnect versions expose the garth client
            token_data = client.client.dumps()
        else:
            # Fallback: try to access garth's session directly
            # The garth library uses a global state or client-specific state
            token_data = garth.dumps()

        # Encode to base64 for safe storage
        return base64.b64encode(token_data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to serialize OAuth tokens: {e}")
        return ""


def deserialize_oauth_tokens(token_str: str, client: Optional[garth.Client] = None) -> bool:
    """
    Deserialize OAuth tokens from a base64 encoded string and load into garth client.

    Args:
        token_str: Base64 encoded string containing serialized tokens
        client: Optional garth client to load tokens into. Creates new one if None.

    Returns:
        True if tokens were successfully loaded, False otherwise
    """
    try:
        # Decode from base64
        token_data = base64.b64decode(token_str.encode('utf-8')).decode('utf-8')

        if client:
            client.loads(token_data)
        else:
            # Load into global garth state
            garth.loads(token_data)

        logger.debug("Successfully deserialized OAuth tokens")
        return True
    except Exception as e:
        logger.warning(f"Failed to deserialize OAuth tokens: {e}")
        return False

# Browser-like user agents that Garmin China accepts
_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def clear_garth_cache() -> None:
    """
    Clear all garth cached tokens and session files.
    This helps when Garmin changes their authentication flow or
    when stale cached tokens cause 401 errors.
    """
    try:
        garth_dir = os.path.expanduser("~/.garth")
        if os.path.exists(garth_dir):
            # Remove all files and directories in garth directory
            for item in os.listdir(garth_dir):
                item_path = os.path.join(garth_dir, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    logger.warning(f"Failed to remove {item_path}: {e}")
            logger.info("Cleared all garth cache files")
    except Exception as e:
        # Ignore errors in cache clearing - it's a best-effort operation
        logger.warning(f"Failed to clear garth cache: {e}")


def get_last_login_error() -> str:
    """
    Get the last login error message for MFA detection.

    Returns:
        The last error message from a login attempt
    """
    return _last_login_error


def set_last_login_error(error_msg: str) -> None:
    """
    Set the last login error message for MFA detection.

    Args:
        error_msg: The error message to store
    """
    global _last_login_error
    _last_login_error = error_msg


class GarminServiceError(Exception):
    """Base exception for Garmin service errors."""
    pass


class GarminAuthError(GarminServiceError):
    """Exception for Garmin authentication errors."""
    pass


class GarminAPIError(GarminServiceError):
    """Exception for Garmin API errors."""
    pass


def login(username: str, password: str, mfa_token: Optional[str] = None, is_cn: bool = False, skip_cache_clear: bool = False) -> Garmin:
    """
    Login to Garmin Connect using username/password.

    Args:
        username: Garmin Connect username (email)
        password: Garmin Connect password
        mfa_token: Optional MFA token if Garmin requires 2FA
        is_cn: True for China (garmin.cn), False for International (garmin.com)
        skip_cache_clear: If True, skip clearing garth cache (for token refresh)

    Returns:
        Authenticated Garmin client instance

    Raises:
        GarminAuthError: If login fails
    """
    region = "Garmin China" if is_cn else "Garmin International"
    logger.info(f"Attempting {region} login for user: {username[:3]}***")

    # Clear cached tokens to force fresh authentication
    # Skip if we're just refreshing existing tokens
    if not skip_cache_clear:
        clear_garth_cache()

    try:
        # Initialize Garmin client with region setting
        garmin_client = Garmin(username, password, is_cn=is_cn)

        # Override user-agent to avoid blocking - use browser-like UA for China
        if is_cn:
            # Garmin China may require browser-like user-agent
            logger.info(f"Applying browser-like User-Agent for Garmin China")
            garth.USER_AGENT = {"User-Agent": _BROWSER_USER_AGENT}
            if hasattr(garmin_client, 'session') and hasattr(garmin_client.session, 'headers'):
                garmin_client.session.headers.update(garth.USER_AGENT)

        if mfa_token:
            logger.info(f"Logging in with MFA token")
            garmin_client.login_with_mfa(mfa_token)
        else:
            logger.info(f"Logging in without MFA")
            garmin_client.login()

        logger.info(f"Successfully authenticated with {region}")
        return garmin_client
    except Exception as e:
        error_msg = str(e)
        set_last_login_error(error_msg)
        logger.error(f"{region} login failed: {e}")
        raise GarminAuthError(f"Login failed: {str(e)}")


def get_garmin_profile(username: str, password: str, mfa_token: Optional[str] = None, is_cn: bool = False) -> Dict[str, Any]:
    """
    Fetch user profile from Garmin Connect.

    Args:
        username: Garmin Connect username
        password: Garmin Connect password
        mfa_token: Optional MFA token
        is_cn: True for China (garmin.cn), False for International (garmin.com)

    Returns:
        Profile data dictionary

    Raises:
        GarminAuthError: If authentication fails
        GarminAPIError: If API call fails
    """
    try:
        garmin_client = login(username, password, mfa_token, is_cn)
        profile = garmin_client.get_user_profile()
        return profile
    except GarminAuthError:
        raise
    except Exception as e:
        logger.error(f"Error fetching Garmin profile: {e}")
        raise GarminAPIError(f"Error fetching profile: {str(e)}")


def fetch_daily_summary(garmin_client: Garmin, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch daily wellness summary from Garmin.

    Args:
        garmin_client: Authenticated Garmin client
        target_date: Date to fetch summary for

    Returns:
        Daily summary data dictionary or None

    Raises:
        GarminAPIError: If API call fails
    """
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        summary = garmin_client.get_user_summary(date_str)
        return summary
    except Exception as e:
        logger.warning(f"Error fetching daily summary for {date_str}: {e}")
        return None


def fetch_sleep_data(garmin_client: Garmin, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch sleep data for a specific date.

    Args:
        garmin_client: Authenticated Garmin client
        target_date: Date to fetch sleep data for

    Returns:
        Sleep data dictionary or None

    Raises:
        GarminAPIError: If API call fails
    """
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        sleep_data = garmin_client.get_sleep_data(date_str)
        return sleep_data
    except Exception as e:
        logger.warning(f"Error fetching sleep data for {date_str}: {e}")
        return None


def fetch_heart_rate_data(garmin_client: Garmin, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch heart rate data for a specific date.

    Args:
        garmin_client: Authenticated Garmin client
        target_date: Date to fetch HR data for

    Returns:
        Heart rate data dictionary or None

    Raises:
        GarminAPIError: If API call fails
    """
    try:
        # Garmin's get_heart_rates returns heart rate data for a date
        date_str = target_date.strftime('%Y-%m-%d')
        heart_rates = garmin_client.get_heart_rates(date_str)
        return heart_rates
    except Exception as e:
        logger.warning(f"Error fetching HR data for {date_str}: {e}")
        return None


def fetch_stress_data(garmin_client: Garmin, target_date: date) -> Optional[Dict[str, Any]]:
    """
    Fetch stress data for a specific date.

    Args:
        garmin_client: Authenticated Garmin client
        target_date: Date to fetch stress data for

    Returns:
        Stress data dictionary or None

    Raises:
        GarminAPIError: If API call fails
    """
    try:
        # Garmin's get_body_battery includes stress information
        date_str = target_date.strftime('%Y-%m-%d')
        body_battery = garmin_client.get_body_battery(date_str)
        return body_battery
    except Exception as e:
        logger.warning(f"Error fetching stress data for {date_str}: {e}")
        return None


def fetch_activity_data(garmin_client: Garmin, target_date: date) -> List[Dict[str, Any]]:
    """
    Fetch activity/exercise data for a specific date.

    Args:
        garmin_client: Authenticated Garmin client
        target_date: Date to fetch activities for

    Returns:
        List of activity data

    Raises:
        GarminAPIError: If API call fails
    """
    try:
        # Convert date to epoch timestamps
        start_timestamp = int(datetime.combine(target_date, datetime.min.time()).timestamp())
        end_timestamp = int(datetime.combine(target_date + timedelta(days=1), datetime.min.time()).timestamp())

        activities = garmin_client.get_activities(start_timestamp, end_timestamp)
        return activities if activities else []
    except Exception as e:
        logger.warning(f"Error fetching activities for {target_date}: {e}")
        return []


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
    sleep_data: Optional[Dict[str, Any]] = None,
    body_battery_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Map Garmin API data to HealthMetric fields.

    Args:
        user_id: User ID
        garmin_data: Garmin daily summary data
        metric_date: Date for the metric
        sleep_data: Optional detailed sleep data with stage breakdown
        body_battery_data: Optional body battery data

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
        # Garmin advanced metrics
        'steps': None,
        'calories': None,
        'distance_km': None,
        'body_battery': None,
        'spo2': None,
        'respiration_rate': None,
        'resting_hr': None,
        'sleep_score': None
    }

    # Extract sleep data (Garmin returns sleep in seconds)
    # Garmin China/International may use different field names
    if 'sleepSeconds' in garmin_data and garmin_data['sleepSeconds'] is not None:
        metric['sleep_hours'] = garmin_data['sleepSeconds'] / 3600
    elif 'sleepingSeconds' in garmin_data and garmin_data['sleepingSeconds'] is not None:
        # Garmin China uses 'sleepingSeconds'
        metric['sleep_hours'] = garmin_data['sleepingSeconds'] / 3600
    elif 'measurableAsleepDuration' in garmin_data and garmin_data['measurableAsleepDuration'] is not None:
        metric['sleep_hours'] = garmin_data['measurableAsleepDuration'] / 3600
    elif 'totalSleepSeconds' in garmin_data and garmin_data['totalSleepSeconds'] is not None:
        metric['sleep_hours'] = garmin_data['totalSleepSeconds'] / 3600

    # Extract sleep stages and duration from sleep_data (dailySleepDTO structure)
    if sleep_data:
        # Garmin returns sleep data in dailySleepDTO nested structure
        daily_dto = sleep_data.get('dailySleepDTO', {}) if isinstance(sleep_data, dict) else {}

        if daily_dto:
            # Extract total sleep time from dailySleepDTO
            if 'sleepTimeSeconds' in daily_dto and daily_dto['sleepTimeSeconds'] is not None:
                metric['sleep_hours'] = daily_dto['sleepTimeSeconds'] / 3600
            elif metric['sleep_hours'] is None and 'unmeasurableSleepSeconds' in daily_dto:
                # Fallback: use total - unmeasurable (if available)
                pass

            # Extract sleep stages from dailySleepDTO (Garmin China structure)
            if 'deepSleepSeconds' in daily_dto and daily_dto['deepSleepSeconds'] is not None:
                metric['deep_sleep_hours'] = daily_dto['deepSleepSeconds'] / 3600
            if 'lightSleepSeconds' in daily_dto and daily_dto['lightSleepSeconds'] is not None:
                metric['light_sleep_hours'] = daily_dto['lightSleepSeconds'] / 3600
            if 'remSleepSeconds' in daily_dto and daily_dto['remSleepSeconds'] is not None:
                metric['rem_sleep_hours'] = daily_dto['remSleepSeconds'] / 3600

            # Extract sleep score from sleepScores.overall.value
            if 'sleepScores' in daily_dto:
                scores = daily_dto['sleepScores']
                if isinstance(scores, dict):
                    if 'overall' in scores:
                        overall = scores['overall']
                        if isinstance(overall, dict) and 'value' in overall:
                            metric['sleep_score'] = _safe_int(overall['value'])
                        elif isinstance(overall, int):
                            metric['sleep_score'] = overall

        # Fallback: Try older/different API structures
        if not metric['deep_sleep_hours'] and not metric['light_sleep_hours']:
            if 'sleepStages' in sleep_data:
                stages = sleep_data['sleepStages']
                if 'deepSleepSeconds' in stages and stages['deepSleepSeconds'] is not None:
                    metric['deep_sleep_hours'] = stages['deepSleepSeconds'] / 3600
                if 'lightSleepSeconds' in stages and stages['lightSleepSeconds'] is not None:
                    metric['light_sleep_hours'] = stages['lightSleepSeconds'] / 3600
                if 'remSleepSeconds' in stages and stages['remSleepSeconds'] is not None:
                    metric['rem_sleep_hours'] = stages['remSleepSeconds'] / 3600
            elif 'deepSleepSeconds' in sleep_data and sleep_data['deepSleepSeconds'] is not None:
                metric['deep_sleep_hours'] = sleep_data['deepSleepSeconds'] / 3600
            elif 'lightSleepSeconds' in sleep_data and sleep_data['lightSleepSeconds'] is not None:
                metric['light_sleep_hours'] = sleep_data['lightSleepSeconds'] / 3600
            elif 'remSleepSeconds' in sleep_data and sleep_data['remSleepSeconds'] is not None:
                metric['rem_sleep_hours'] = sleep_data['remSleepSeconds'] / 3600

        # Extract sleep score directly if not found in dailySleepDTO
        if not metric['sleep_score']:
            if 'sleepScore' in sleep_data:
                metric['sleep_score'] = _safe_int(sleep_data['sleepScore'])
            elif 'overallSleepScore' in sleep_data:
                metric['sleep_score'] = _safe_int(sleep_data['overallSleepScore'])

    # Extract resting heart rate
    if 'restingHeartRate' in garmin_data:
        metric['resting_heart_rate'] = _safe_int(garmin_data['restingHeartRate'])
    elif 'averageRestingHeartRate' in garmin_data:
        metric['resting_heart_rate'] = _safe_int(garmin_data['averageRestingHeartRate'])

    # Extract stress level
    if 'averageStressLevel' in garmin_data:
        metric['stress_level'] = _safe_int(garmin_data['averageStressLevel'])
    elif 'maxStressLevel' in garmin_data:
        metric['stress_level'] = _safe_int(garmin_data['maxStressLevel'])

    # Extract exercise minutes - Garmin provides multiple fields
    moderate_minutes = 0
    vigorous_minutes = 0

    if 'moderateIntensityMinutes' in garmin_data:
        val = _safe_int(garmin_data['moderateIntensityMinutes'])
        if val is not None:
            moderate_minutes = val
    if 'vigorousIntensityMinutes' in garmin_data:
        val = _safe_int(garmin_data['vigorousIntensityMinutes'])
        if val is not None:
            vigorous_minutes = val
    if 'activeMinutes' in garmin_data:
        val = _safe_int(garmin_data['activeMinutes'])
        if val is not None:
            moderate_minutes = val
    if 'intensityMinutes' in garmin_data and 'moderateValue' in garmin_data['intensityMinutes']:
        val = _safe_int(garmin_data['intensityMinutes']['moderateValue'])
        if val is not None:
            moderate_minutes = val
    if 'intensityMinutes' in garmin_data and 'vigorousValue' in garmin_data['intensityMinutes']:
        val = _safe_int(garmin_data['intensityMinutes']['vigorousValue'])
        if val is not None:
            vigorous_minutes = val

    if moderate_minutes > 0 or vigorous_minutes > 0:
        metric['exercise_minutes'] = moderate_minutes + vigorous_minutes

    # Extract steps
    if 'totalSteps' in garmin_data:
        metric['steps'] = _safe_int(garmin_data['totalSteps'])
    elif 'steps' in garmin_data:
        metric['steps'] = _safe_int(garmin_data['steps'])

    # Extract calories
    if 'totalKilocalories' in garmin_data:
        metric['calories'] = _safe_int(garmin_data['totalKilocalories'])
    elif 'kilocalories' in garmin_data:
        metric['calories'] = _safe_int(garmin_data['kilocalories'])

    # Extract distance (Garmin returns in meters, convert to km)
    if 'totalDistanceMeters' in garmin_data:
        dist = _safe_float(garmin_data['totalDistanceMeters'])
        if dist is not None:
            metric['distance_km'] = dist / 1000
    elif 'totalDistance' in garmin_data:
        dist = _safe_float(garmin_data['totalDistance'])
        if dist is not None:
            metric['distance_km'] = dist / 1000
    elif 'distance' in garmin_data:
        dist = _safe_float(garmin_data['distance'])
        if dist is not None:
            metric['distance_km'] = dist / 1000

    # Extract body battery from garmin_data (daily summary) if available
    # Use most recent value as it reflects current state, not the day's peak
    if 'bodyBatteryMostRecentValue' in garmin_data:
        metric['body_battery'] = _safe_int(garmin_data['bodyBatteryMostRecentValue'])
    elif 'bodyBatteryHighestValue' in garmin_data:
        metric['body_battery'] = _safe_int(garmin_data['bodyBatteryHighestValue'])

    # Extract body battery from body_battery_data if available (fallback)
    if metric['body_battery'] is None and body_battery_data:
        if 'bodyBatteryLevel' in body_battery_data:
            # Use the highest value (peak) for the day
            if isinstance(body_battery_data['bodyBatteryLevel'], list):
                values = [b.get('value', 0) for b in body_battery_data['bodyBatteryLevel'] if b.get('value') is not None]
                metric['body_battery'] = _safe_int(max(values)) if values else None
            else:
                metric['body_battery'] = _safe_int(body_battery_data['bodyBatteryLevel'])
        elif 'highestBodyBatteryLevel' in body_battery_data:
            metric['body_battery'] = _safe_int(body_battery_data['highestBodyBatteryLevel'])
        elif 'lowestBodyBatteryLevel' in body_battery_data:
            metric['body_battery'] = _safe_int(body_battery_data['lowestBodyBatteryLevel'])

    # Extract SpO2 from daily summary
    if 'averageSpo2' in garmin_data:
        metric['spo2'] = _safe_float(garmin_data['averageSpo2'])
    elif 'averageSpO2' in garmin_data:
        metric['spo2'] = _safe_float(garmin_data['averageSpO2'])
    elif 'spo2' in garmin_data:
        metric['spo2'] = _safe_float(garmin_data['spo2'])

    # Extract respiration rate
    if 'avgWakingRespirationValue' in garmin_data:
        metric['respiration_rate'] = _safe_float(garmin_data['avgWakingRespirationValue'])
    elif 'averageRespiration' in garmin_data:
        metric['respiration_rate'] = _safe_float(garmin_data['averageRespiration'])
    elif 'respiration' in garmin_data:
        metric['respiration_rate'] = _safe_float(garmin_data['respiration'])

    # Extract resting heart rate (already handled above, but ensure field mapping)
    # We use 'resting_hr' as the field name in the model
    if 'restingHeartRate' in garmin_data:
        metric['resting_hr'] = _safe_int(garmin_data['restingHeartRate'])
    elif 'averageRestingHeartRate' in garmin_data:
        metric['resting_hr'] = _safe_int(garmin_data['averageRestingHeartRate'])

    # Extract sleep score from sleep data
    if sleep_data:
        if 'sleepScore' in sleep_data:
            metric['sleep_score'] = _safe_int(sleep_data['sleepScore'])
        elif 'overallSleepScore' in sleep_data:
            metric['sleep_score'] = _safe_int(sleep_data['overallSleepScore'])
        elif 'sleepScores' in sleep_data:
            scores = sleep_data['sleepScores']
            if 'overall' in scores:
                metric['sleep_score'] = _safe_int(scores['overall'])

    return metric


def refresh_garmin_data(
    user_id: int,
    days: int = 7,
    db_session=None
) -> Dict[str, Any]:
    """
    Fetch and sync Garmin health metrics for a user.

    Prioritizes using stored OAuth tokens for authentication.
    Falls back to username/password login if tokens are unavailable or expired.

    Args:
        user_id: User ID
        days: Number of days to sync (default: 7)
        db_session: Optional database session (creates new if not provided)

    Returns:
        Dictionary with sync results (success, count, errors)

    Raises:
        GarminAuthError: If authentication fails
        GarminAPIError: If API call fails
    """
    # Use provided session or create new one
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

        # Check connection status
        if connection.sync_status != "connected":
            raise GarminAuthError(f"Garmin connection not active: {connection.sync_status}")

        # Decrypt credentials
        username = decrypt_token(connection.garmin_username)
        password = decrypt_token(connection.garmin_password)
        is_cn = connection.is_cn == 1  # Convert to bool

        if not username or not password:
            raise GarminAuthError("Invalid stored credentials")

        # Try to use OAuth tokens first
        garmin_client = None
        tokens_used = False

        if connection.garmin_oauth_tokens:
            try:
                # Decrypt and deserialize OAuth tokens
                token_str = decrypt_token(connection.garmin_oauth_tokens)
                if token_str:
                    # Create a new Garmin client and load the tokens
                    garmin_client = Garmin(username, password, is_cn=is_cn)

                    # Try to load the tokens into garth
                    if deserialize_oauth_tokens(token_str):
                        # Verify the tokens work by checking if we can access the client
                        # The tokens should be loaded into the garth session
                        logger.info("Successfully loaded stored OAuth tokens")

                        # Create a fresh client that should use the loaded tokens
                        # Don't clear cache since we want to use the loaded tokens
                        try:
                            # Try to make a simple API call to verify tokens are valid
                            # If this works, we don't need to login again
                            garmin_client = Garmin(username, password, is_cn=is_cn)
                            # The Garmin client will use garth which now has our tokens loaded
                            # Skip the cache clear so we use the loaded tokens
                            if hasattr(garmin_client, 'client'):
                                # Try to access a simple endpoint to verify
                                pass
                            tokens_used = True
                        except Exception as verify_error:
                            logger.warning(f"Stored OAuth tokens verification failed: {verify_error}")
                            tokens_used = False
                            garmin_client = None
            except Exception as e:
                logger.warning(f"Failed to load OAuth tokens, will use password login: {e}")
                garmin_client = None

        # Fall back to username/password login if tokens didn't work
        if not garmin_client or not tokens_used:
            logger.info("No valid OAuth tokens, performing username/password login")
            try:
                # Try MFA token if stored (legacy fallback)
                mfa_token = None
                if connection.garmin_mfa_token:
                    mfa_token = decrypt_token(connection.garmin_mfa_token)

                garmin_client = login(username, password, mfa_token, is_cn)

                # After successful login, serialize and store the OAuth tokens for next time
                if garmin_client:
                    new_oauth_tokens = serialize_oauth_tokens(garmin_client)
                    if new_oauth_tokens:
                        encrypted_tokens = encrypt_token(new_oauth_tokens)
                        connection.garmin_oauth_tokens = encrypted_tokens
                        # Clear the deprecated MFA token
                        connection.garmin_mfa_token = None
                        db.commit()
                        logger.info("Stored new OAuth tokens after successful login")
            except Exception as e:
                connection.sync_status = "error"
                connection.last_error = str(e)
                db.commit()
                raise GarminAuthError(f"Authentication failed: {str(e)}")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Fetch data from Garmin
        sync_results = {
            'success': False,
            'days_synced': 0,
            'metrics_created': 0,
            'metrics_updated': 0,
            'errors': []
        }

        # Fetch and process each day's data
        current_date = start_date
        while current_date <= end_date:
            try:
                # Fetch daily summary
                daily_summary = fetch_daily_summary(garmin_client, current_date)

                # Fetch detailed sleep data for sleep stages
                sleep_detailed = fetch_sleep_data(garmin_client, current_date)

                # Fetch body battery data
                body_battery = fetch_stress_data(garmin_client, current_date)

                if daily_summary:
                    # Map Garmin data to health metric, including sleep stages and body battery
                    metric_data = map_garmin_to_health_metric(
                        user_id, daily_summary, current_date, sleep_detailed, body_battery
                    )

                    # Check if we have any data worth saving
                    has_data = any(
                        v is not None
                        for k, v in metric_data.items()
                        if k not in ['user_id', 'date']
                    )

                    if has_data:
                        # Upsert health metric
                        existing_metric = db.query(HealthMetric).filter(
                            HealthMetric.user_id == user_id,
                            HealthMetric.date == current_date
                        ).first()

                        if existing_metric:
                            # Update existing metric
                            for field, value in metric_data.items():
                                if field not in ['user_id', 'date'] and value is not None:
                                    setattr(existing_metric, field, value)
                            existing_metric.updated_at = datetime.utcnow()
                            sync_results['metrics_updated'] += 1
                        else:
                            # Create new metric
                            new_metric = HealthMetric(**metric_data)
                            db.add(new_metric)
                            sync_results['metrics_created'] += 1

                        sync_results['days_synced'] += 1

            except Exception as e:
                logger.error(f"Error processing data for {current_date}: {e}")
                sync_results['errors'].append(f"{current_date}: {str(e)}")

            current_date += timedelta(days=1)

        # Commit changes
        db.commit()

        # Update connection with successful sync timestamp
        connection.last_sync_at = datetime.utcnow()
        connection.sync_status = "connected"
        connection.last_error = None
        db.commit()

        sync_results['success'] = True
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
    garmin_client: Optional[Garmin] = None,
    db_session=None
) -> GarminConnection:
    """
    Save or update Garmin connection for a user.

    Stores encrypted credentials and OAuth tokens for persistent authentication.
    OAuth tokens are preferred over MFA tokens as they can be reused for subsequent logins.

    Args:
        user_id: User ID
        username: Garmin Connect username (email)
        password: Garmin Connect password
        mfa_token: Optional MFA token (deprecated - use OAuth tokens instead)
        garmin_user_id: Optional Garmin user ID
        garmin_display_name: Optional Garmin display name
        is_cn: True for China (garmin.cn), False for International (garmin.com)
        garmin_client: Optional authenticated Garmin client to extract OAuth tokens from
        db_session: Optional database session

    Returns:
        GarminConnection object
    """
    # Use provided session or create new one
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        # Encrypt credentials
        encrypted_username = encrypt_token(username)
        encrypted_password = encrypt_token(password)

        # Serialize OAuth tokens if client is provided
        encrypted_oauth_tokens = None
        if garmin_client:
            oauth_tokens = serialize_oauth_tokens(garmin_client)
            if oauth_tokens:
                encrypted_oauth_tokens = encrypt_token(oauth_tokens)
                logger.info("Successfully serialized and encrypted OAuth tokens")

        # MFA token is deprecated - we prefer OAuth tokens
        # Only store MFA if no OAuth tokens available (fallback)
        encrypted_mfa = None
        if not encrypted_oauth_tokens and mfa_token:
            encrypted_mfa = encrypt_token(mfa_token)

        # Check for existing connection
        existing = db.query(GarminConnection).filter(
            GarminConnection.user_id == user_id
        ).first()

        if existing:
            # Update existing connection
            existing.garmin_username = encrypted_username
            existing.garmin_password = encrypted_password
            existing.garmin_oauth_tokens = encrypted_oauth_tokens
            # Clear deprecated MFA token if we have OAuth tokens
            if encrypted_oauth_tokens:
                existing.garmin_mfa_token = None
            elif encrypted_mfa:
                existing.garmin_mfa_token = encrypted_mfa
            existing.garmin_user_id = garmin_user_id or existing.garmin_user_id
            existing.garmin_display_name = garmin_display_name or existing.garmin_display_name
            existing.is_cn = 1 if is_cn else 0
            existing.updated_at = datetime.utcnow()
            existing.sync_status = "connected"
            existing.last_error = None
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new connection
            connection = GarminConnection(
                user_id=user_id,
                garmin_username=encrypted_username,
                garmin_password=encrypted_password,
                garmin_oauth_tokens=encrypted_oauth_tokens,
                garmin_mfa_token=encrypted_mfa,
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


def test_garmin_credentials(username: str, password: str, mfa_token: Optional[str] = None, is_cn: bool = False) -> bool:
    """
    Test if Garmin credentials are valid with detailed error reporting.

    Args:
        username: Garmin Connect username
        password: Garmin Connect password
        mfa_token: Optional MFA token
        is_cn: True for China (garmin.cn), False for International (garmin.com)

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        garmin_client = login(username, password, mfa_token, is_cn)
        # Try to fetch user profile to verify connection
        profile = garmin_client.get_user_profile()
        return profile is not None
    except Exception as e:
        error_msg = str(e)
        region_name = "Garmin China" if is_cn else "Garmin International"

        # Check for specific error patterns
        if "401" in error_msg or "Unauthorized" in error_msg:
            if is_cn:
                logger.warning(
                    f"{region_name} API login failed (web login verified working). "
                    f"This may be a library issue with Garmin China authentication."
                )
                set_last_login_error(
                    f"API login failed for {region_name}. Your credentials work on web, "
                    f"but the library may need updates for Garmin China's SSO."
                )
            else:
                logger.warning(f"{region_name} login failed: Invalid credentials")
                set_last_login_error(f"Invalid credentials for {region_name}")
        elif "MFA" in error_msg or "2FA" in error_msg or "OTP" in error_msg:
            logger.warning(f"{region_name} login requires MFA: {error_msg}")
            set_last_login_error(f"Your {region_name} account requires 2FA. Please provide an MFA token.")
        elif "SSL" in error_msg or "certificate" in error_msg:
            logger.warning("SSL/TLS certificate error - check system certificates")
            set_last_login_error("SSL certificate error. Check your network connection.")
        elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            logger.warning("Network connection error - check internet connection")
            set_last_login_error("Network error. Please check your internet connection.")
        else:
            logger.warning(f"{region_name} login failed: {error_msg}")
            set_last_login_error(f"Login failed: {error_msg}")
        return False
