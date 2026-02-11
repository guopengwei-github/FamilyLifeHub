# ABOUTME: Garmin Connect service for OAuth authentication and health data sync
# ABOUTME: Handles username/password login, MFA flow, token persistence, and data ingestion
import garth
from garth.http import Client
from garth.sso import login as garth_login, resume_login
from garth.exc import GarthHTTPError, GarthException
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
import logging
import secrets
import base64
import pickle

from app.core.security import encrypt_token, decrypt_token
from app.models import User, GarminConnection, HealthMetric
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
    now = datetime.utcnow()
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
        "created_at": datetime.utcnow()
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
            import traceback
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
) -> Dict[str, Any]:
    """
    Map Garmin API data to HealthMetric fields.

    Args:
        user_id: User ID
        garmin_data: Garmin daily summary data from dailySleepData endpoint
        metric_date: Date for the metric

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
        'sleep_score': None
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

    # Extract body battery
    if 'sleepBodyBattery' in garmin_data and garmin_data['sleepBodyBattery']:
        bb_values = [b.get('value') for b in garmin_data['sleepBodyBattery'] if b.get('value') is not None]
        if bb_values:
            metric['body_battery'] = _safe_int(bb_values[-1])

    # Extract SpO2
    if 'wellnessSpO2SleepSummaryDTO' in garmin_data and garmin_data['wellnessSpO2SleepSummaryDTO']:
        spo2_data = garmin_data['wellnessSpO2SleepSummaryDTO']
        if 'avgSpO2' in spo2_data:
            metric['spo2'] = _safe_float(spo2_data['avgSpO2'])

    # Extract respiration
    if 'wellnessEpochRespirationAveragesList' in garmin_data and garmin_data['wellnessEpochRespirationAveragesList']:
        resp_values = [r.get('breathsPerMinute') for r in garmin_data['wellnessEpochRespirationAveragesList'] if r.get('breathsPerMinute') is not None]
        if resp_values:
            metric['respiration_rate'] = _safe_float(sum(resp_values) / len(resp_values))

    return metric


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
            'errors': []
        }

        current_date = start_date
        while current_date <= end_date:
            try:
                logger.info(f"Fetching data for {current_date}")

                daily_summary = fetch_daily_summary(client, current_date)

                if not daily_summary:
                    logger.warning(f"No daily_summary data for {current_date}, skipping")
                    current_date += timedelta(days=1)
                    continue

                metric_data = map_garmin_to_health_metric(user_id, daily_summary, current_date)

                # Check if we have any data worth saving
                has_data = any(
                    v is not None
                    for k, v in metric_data.items()
                    if k not in ['user_id', 'date']
                )

                if has_data:
                    existing_metric = db.query(HealthMetric).filter(
                        HealthMetric.user_id == user_id,
                        HealthMetric.date == current_date
                    ).first()

                    if existing_metric:
                        for field, value in metric_data.items():
                            if field not in ['user_id', 'date'] and value is not None:
                                setattr(existing_metric, field, value)
                        existing_metric.updated_at = datetime.utcnow()
                        sync_results['metrics_updated'] += 1
                    else:
                        new_metric = HealthMetric(**metric_data)
                        db.add(new_metric)
                        sync_results['metrics_created'] += 1

                    sync_results['days_synced'] += 1

            except Exception as e:
                logger.error(f"Error processing data for {current_date}: {e}")
                sync_results['errors'].append(f"{current_date}: {str(e)}")

            current_date += timedelta(days=1)

        # Commit changes and update connection
        db.commit()
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
            existing.updated_at = datetime.utcnow()
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
