"""
Strava API service for syncing activity data.
Uses OAuth2 authorization code flow with token refresh support.
"""
import httpx
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import logging
import calendar
from urllib.parse import urlencode

from app.core.security import encrypt_token, decrypt_token
from app.core.config import settings
from app.models import User, StravaConnection, ActivityMetric, HealthMetric
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Strava API endpoints
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


class StravaServiceError(Exception):
    """Base exception for Strava service errors."""
    pass


class StravaAuthError(StravaServiceError):
    """Exception for Strava authentication errors."""
    pass


class StravaAPIError(StravaServiceError):
    """Exception for Strava API errors."""
    pass


def get_authorization_url(client_id: str, redirect_uri: str, state: Optional[str] = None) -> str:
    """
    Generate Strava OAuth2 authorization URL.

    Args:
        client_id: Strava Client ID from user's configuration
        redirect_uri: OAuth callback URL
        state: Optional state parameter for CSRF protection

    Returns:
        Authorization URL to redirect user to Strava

    Raises:
        StravaAuthError: If Strava client ID is not provided
    """
    if not client_id:
        raise StravaAuthError("Strava client ID not configured")

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "activity:read_all,activity:write,read_all",
        "approval_prompt": "auto",
    }

    if state:
        params["state"] = state

    return f"{STRAVA_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(client_id: str, client_secret: str, code: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        client_id: Strava Client ID from user's configuration
        client_secret: Strava Client Secret from user's configuration
        code: Authorization code from Strava callback

    Returns:
        Dictionary with tokens: access_token, refresh_token, expires_at, athlete

    Raises:
        StravaAuthError: If token exchange fails
    """
    if not client_id or not client_secret:
        raise StravaAuthError("Strava client credentials not configured")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(STRAVA_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava token exchange failed: {e.response.text}")
        raise StravaAuthError(f"Failed to exchange code for token: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Strava token exchange error: {e}")
        raise StravaAuthError(f"Token exchange failed: {str(e)}")


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> Dict[str, Any]:
    """
    Refresh an expired access token using refresh token.

    Args:
        client_id: Strava Client ID from user's configuration
        client_secret: Strava Client Secret from user's configuration
        refresh_token: Valid refresh token

    Returns:
        Dictionary with new tokens: access_token, refresh_token, expires_at

    Raises:
        StravaAuthError: If token refresh fails
    """
    if not client_id or not client_secret:
        raise StravaAuthError("Strava client credentials not configured")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(STRAVA_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava token refresh failed: {e.response.text}")
        raise StravaAuthError(f"Failed to refresh token: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Strava token refresh error: {e}")
        raise StravaAuthError(f"Token refresh failed: {str(e)}")


def get_athlete(access_token: str) -> Dict[str, Any]:
    """
    Fetch current athlete profile from Strava.

    Args:
        access_token: Valid Strava access token

    Returns:
        Athlete data dictionary

    Raises:
        StravaAPIError: If API call fails
        StravaAuthError: If token is invalid
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{STRAVA_API_BASE}/athlete",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 401:
                raise StravaAuthError("Invalid or expired access token")
            response.raise_for_status()
            return response.json()
    except StravaAuthError:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava athlete fetch failed: {e.response.text}")
        raise StravaAPIError(f"Failed to fetch athlete: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Strava athlete fetch error: {e}")
        raise StravaAPIError(f"Failed to fetch athlete: {str(e)}")


def fetch_activities(
    access_token: str,
    before: Optional[int] = None,
    after: Optional[int] = None,
    per_page: int = 30,
    page: int = 1
) -> List[Dict[str, Any]]:
    """
    Fetch activity list from Strava.

    Args:
        access_token: Valid Strava access token
        before: Unix timestamp (exclusive) - only return activities before this time
        after: Unix timestamp (exclusive) - only return activities after this time
        per_page: Number of items per page (max 200)
        page: Page number

    Returns:
        List of activity data dictionaries

    Raises:
        StravaAPIError: If API call fails
        StravaAuthError: If token is invalid
    """
    params = {
        "per_page": min(per_page, 200),
        "page": page,
    }

    if before:
        params["before"] = before
    if after:
        params["after"] = after

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params
            )
            if response.status_code == 401:
                raise StravaAuthError("Invalid or expired access token")
            if response.status_code == 429:
                raise StravaAPIError("Strava API rate limit exceeded (200 requests/day)")
            response.raise_for_status()
            return response.json()
    except StravaAuthError:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava activities fetch failed: {e.response.text}")
        raise StravaAPIError(f"Failed to fetch activities: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Strava activities fetch error: {e}")
        raise StravaAPIError(f"Failed to fetch activities: {str(e)}")


def fetch_activity_details(access_token: str, activity_id: int) -> Dict[str, Any]:
    """
    Fetch detailed activity data from Strava.

    Args:
        access_token: Valid Strava access token
        activity_id: Strava activity ID

    Returns:
        Detailed activity data dictionary

    Raises:
        StravaAPIError: If API call fails
        StravaAuthError: If token is invalid
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 401:
                raise StravaAuthError("Invalid or expired access token")
            response.raise_for_status()
            return response.json()
    except StravaAuthError:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Strava activity detail fetch failed: {e.response.text}")
        raise StravaAPIError(f"Failed to fetch activity details: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Strava activity detail fetch error: {e}")
        raise StravaAPIError(f"Failed to fetch activity details: {str(e)}")


def map_strava_to_activity_metric(user_id: int, strava_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Strava activity data to ActivityMetric fields.

    Args:
        user_id: User ID
        strava_data: Strava activity data from API

    Returns:
        Dictionary with ActivityMetric fields
    """
    # Parse dates from Strava (returns ISO 8601 strings)
    start_date = None
    start_date_local = None
    activity_date = None

    if "start_date" in strava_data:
        try:
            start_date = datetime.fromisoformat(strava_data["start_date"].replace("Z", "+00:00"))
            activity_date = start_date.date()
        except (ValueError, TypeError):
            pass

    if "start_date_local" in strava_data:
        try:
            start_date_local = datetime.fromisoformat(strava_data["start_date_local"])
            if not activity_date:
                activity_date = start_date_local.date()
        except (ValueError, TypeError):
            pass

    metric = {
        'user_id': user_id,
        'strava_activity_id': strava_data.get('id'),
        'date': activity_date or date.today(),
        'activity_type': strava_data.get('type') or strava_data.get('sport_type'),
        'name': strava_data.get('name'),
        'distance_meters': strava_data.get('distance'),
        'moving_time_seconds': strava_data.get('moving_time'),
        'elapsed_time_seconds': strava_data.get('elapsed_time'),
        'average_speed_mps': strava_data.get('average_speed'),
        'max_speed_mps': strava_data.get('max_speed'),
        'average_heartrate': strava_data.get('average_heartrate'),
        'max_heartrate': strava_data.get('max_heartrate'),
        'elevation_gain_meters': strava_data.get('total_elevation_gain'),
        'calories': strava_data.get('calories'),
        'start_date': start_date,
        'start_date_local': start_date_local,
    }

    return metric


def ensure_valid_token(connection: StravaConnection) -> str:
    """
    Ensure access token is valid, refresh if needed.

    Args:
        connection: StravaConnection object

    Returns:
        Valid access token

    Raises:
        StravaAuthError: If token refresh fails
    """
    current_time = int(datetime.utcnow().timestamp())

    # Get client credentials
    client_id = decrypt_token(connection.strava_client_id) if connection.strava_client_id else None
    client_secret = decrypt_token(connection.strava_client_secret) if connection.strava_client_secret else None

    if not client_id or not client_secret:
        raise StravaAuthError("Strava app credentials not configured")

    # Refresh if token expires in less than 5 minutes or has already expired
    if not connection.strava_token_expires_at or connection.strava_token_expires_at < current_time + 300:
        logger.info(f"Refreshing Strava token for user {connection.user_id}")

        try:
            refresh_token = decrypt_token(connection.strava_refresh_token)
            if not refresh_token:
                raise StravaAuthError("Invalid refresh token")

            token_response = refresh_access_token(client_id, client_secret, refresh_token)

            # Update connection with new tokens
            connection.strava_access_token = encrypt_token(token_response["access_token"])
            connection.strava_refresh_token = encrypt_token(token_response["refresh_token"])
            connection.strava_token_expires_at = token_response["expires_at"]
            connection.updated_at = datetime.utcnow()
            connection.sync_status = "connected"
            connection.last_error = None

            return token_response["access_token"]
        except Exception as e:
            connection.sync_status = "error"
            connection.last_error = f"Token refresh failed: {str(e)}"
            raise StravaAuthError(f"Failed to refresh token: {str(e)}")

    # Token is still valid
    return decrypt_token(connection.strava_access_token)


def save_strava_connection(
    user_id: int,
    access_token: str,
    refresh_token: str,
    expires_at: int,
    athlete_data: Optional[Dict[str, Any]] = None,
    db_session=None
) -> StravaConnection:
    """
    Save or update Strava OAuth connection for a user.

    Args:
        user_id: User ID
        access_token: OAuth access token
        refresh_token: OAuth refresh token
        expires_at: Token expiration timestamp (Unix)
        athlete_data: Optional athlete data from Strava
        db_session: Optional database session

    Returns:
        StravaConnection object
    """
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        # Extract athlete info if provided
        strava_athlete_id = athlete_data.get("id") if athlete_data else None
        strava_athlete_name = None
        strava_athlete_profile = None

        if athlete_data:
            strava_athlete_name = athlete_data.get("firstname", "") + " " + athlete_data.get("lastname", "")
            strava_athlete_name = strava_athlete_name.strip() or None
            strava_athlete_profile = athlete_data.get("profile")

        # Encrypt tokens
        encrypted_access = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token)

        # Check for existing connection
        existing = db.query(StravaConnection).filter(
            StravaConnection.user_id == user_id
        ).first()

        if existing:
            # Update existing connection
            existing.strava_access_token = encrypted_access
            existing.strava_refresh_token = encrypted_refresh
            existing.strava_token_expires_at = expires_at
            existing.strava_athlete_id = strava_athlete_id or existing.strava_athlete_id
            existing.strava_athlete_name = strava_athlete_name or existing.strava_athlete_name
            existing.strava_athlete_profile = strava_athlete_profile or existing.strava_athlete_profile
            existing.updated_at = datetime.utcnow()
            existing.sync_status = "connected"
            existing.last_error = None
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new connection
            connection = StravaConnection(
                user_id=user_id,
                strava_access_token=encrypted_access,
                strava_refresh_token=encrypted_refresh,
                strava_token_expires_at=expires_at,
                strava_athlete_id=strava_athlete_id,
                strava_athlete_name=strava_athlete_name,
                strava_athlete_profile=strava_athlete_profile,
                sync_status="connected"
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)
            return connection

    finally:
        if close_session:
            db.close()


def refresh_strava_data(
    user_id: int,
    days: int = 30,
    db_session=None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch and sync Strava activity data for a user.

    Args:
        user_id: User ID
        days: Number of days to sync (default: 30)
        db_session: Optional database session

    Returns:
        Dictionary with sync results (success, count, errors)

    Raises:
        StravaAuthError: If authentication fails
        StravaAPIError: If API call fails
    """
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        # Get user's Strava connection
        connection = db.query(StravaConnection).filter(
            StravaConnection.user_id == user_id
        ).first()

        if not connection:
            raise StravaAuthError("No Strava connection found for user")

        # Check connection status
        if connection.sync_status != "connected":
            raise StravaAuthError(f"Strava connection not active: {connection.sync_status}")

        # Get valid access token (refresh if needed)
        access_token = ensure_valid_token(connection)

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Convert to Unix timestamps for Strava API
        after_timestamp = int(start_date.timestamp())
        before_timestamp = int(end_date.timestamp())

        sync_results = {
            'success': False,
            'activities_synced': 0,
            'metrics_updated': 0,
            'errors': []
        }

        # Fetch activities from Strava (may need pagination)
        all_activities = []
        page = 1
        per_page = 200  # Maximum per page

        while True:
            activities = fetch_activities(
                access_token=access_token,
                before=before_timestamp,
                after=after_timestamp,
                per_page=per_page,
                page=page
            )

            if not activities:
                break

            all_activities.extend(activities)

            # Check if we got a full page (more might be available)
            if len(activities) < per_page:
                break

            page += 1

            # Safety limit to prevent infinite loops
            if page > 10:
                logger.warning(f"Reached pagination limit at page {page}")
                break

        logger.info(f"Fetched {len(all_activities)} activities for user {user_id}")

        # Process each activity
        for activity in all_activities:
            try:
                strava_id = activity.get('id')
                if not strava_id:
                    continue

                # Map Strava data to our model
                metric_data = map_strava_to_activity_metric(user_id, activity)

                # Check if activity already exists
                existing_activity = db.query(ActivityMetric).filter(
                    ActivityMetric.strava_activity_id == strava_id
                ).first()

                if existing_activity:
                    # Update existing activity
                    for field, value in metric_data.items():
                        if field != 'user_id' and value is not None:
                            setattr(existing_activity, field, value)
                    sync_results['activities_synced'] += 1
                else:
                    # Create new activity
                    new_activity = ActivityMetric(**metric_data)
                    db.add(new_activity)
                    sync_results['activities_synced'] += 1

                # Also update health metrics with exercise time from this activity
                activity_date = metric_data['date']
                moving_seconds = metric_data.get('moving_time_seconds')
                if moving_seconds:
                    exercise_minutes = int(moving_seconds / 60)

                    # Find or create health metric for this date
                    existing_health = db.query(HealthMetric).filter(
                        HealthMetric.user_id == user_id,
                        HealthMetric.date == activity_date
                    ).first()

                    if existing_health:
                        # Accumulate exercise minutes
                        if existing_health.exercise_minutes is None:
                            existing_health.exercise_minutes = exercise_minutes
                        else:
                            existing_health.exercise_minutes += exercise_minutes
                        existing_health.updated_at = datetime.utcnow()
                    else:
                        new_health = HealthMetric(
                            user_id=user_id,
                            date=activity_date,
                            exercise_minutes=exercise_minutes
                        )
                        db.add(new_health)
                    sync_results['metrics_updated'] += 1

            except Exception as e:
                logger.error(f"Error processing Strava activity {activity.get('id')}: {e}")
                sync_results['errors'].append(f"Activity {activity.get('id')}: {str(e)}")

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


def delete_strava_connection(user_id: int, db_session=None) -> bool:
    """
    Delete Strava connection for a user.

    Args:
        user_id: User ID
        db_session: Optional database session

    Returns:
        True if connection was deleted, False if not found
    """
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        connection = db.query(StravaConnection).filter(
            StravaConnection.user_id == user_id
        ).first()

        if connection:
            db.delete(connection)
            db.commit()
            return True
        return False

    finally:
        if close_session:
            db.close()


def save_strava_app_config(
    user_id: int,
    client_id: str,
    client_secret: str,
    db_session=None
) -> StravaConnection:
    """
    Save or update Strava app credentials for a user.

    Args:
        user_id: User ID
        client_id: Strava Client ID
        client_secret: Strava Client Secret
        db_session: Optional database session

    Returns:
        StravaConnection object with credentials saved
    """
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        # Check for existing connection
        existing = db.query(StravaConnection).filter(
            StravaConnection.user_id == user_id
        ).first()

        encrypted_client_id = encrypt_token(client_id)
        encrypted_client_secret = encrypt_token(client_secret)

        if existing:
            # Update existing connection
            existing.strava_client_id = encrypted_client_id
            existing.strava_client_secret = encrypted_client_secret
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new connection with app config only
            connection = StravaConnection(
                user_id=user_id,
                strava_client_id=encrypted_client_id,
                strava_client_secret=encrypted_client_secret,
                strava_access_token="",  # Will be set after OAuth
                strava_refresh_token="",
                strava_token_expires_at=0,
                sync_status="config_set"  # New status indicating config is set but not connected
            )
            db.add(connection)
            db.commit()
            db.refresh(connection)
            return connection

    finally:
        if close_session:
            db.close()


def get_strava_app_config(user_id: int, db_session=None) -> Optional[Dict[str, str]]:
    """
    Get user's Strava app credentials.

    Args:
        user_id: User ID
        db_session: Optional database session

    Returns:
        Dictionary with client_id and client_secret, or None if not configured
    """
    close_session = False
    if db_session is None:
        db = SessionLocal()
        close_session = True
    else:
        db = db_session

    try:
        connection = db.query(StravaConnection).filter(
            StravaConnection.user_id == user_id
        ).first()

        if not connection or not connection.strava_client_id or not connection.strava_client_secret:
            return None

        return {
            "client_id": decrypt_token(connection.strava_client_id),
            "client_secret": decrypt_token(connection.strava_client_secret)
        }

    finally:
        if close_session:
            db.close()


def has_strava_app_config(user_id: int, db_session=None) -> bool:
    """
    Check if user has configured Strava app credentials.

    Args:
        user_id: User ID
        db_session: Optional database session

    Returns:
        True if user has configured credentials, False otherwise
    """
    config = get_strava_app_config(user_id, db_session)
    return config is not None
