"""
Strava API endpoints.
Handles OAuth2 authorization, connection management, and data synchronization for Strava.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date as date_type, datetime
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models import User, StravaConnection, ActivityMetric
from app.services import strava as strava_service
from app.schemas import (
    StravaAuthUrlResponse,
    StravaCallbackRequest,
    StravaConnectionResponse,
    StravaSyncRequest,
    StravaSyncResponse,
    StravaActivityResponse,
    StravaActivitiesResponse,
    StravaAppConfig,
    StravaAppConfigResponse
)

router = APIRouter(prefix="/strava", tags=["Strava"])


@router.get("/config", response_model=StravaAppConfigResponse)
async def get_strava_config(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's Strava app configuration status.

    Returns whether the user has configured their Strava app credentials.

    Requires authentication.
    """
    has_config = strava_service.has_strava_app_config(current_user.id)
    return StravaAppConfigResponse(has_config=has_config)


@router.post("/config")
async def save_strava_config(
    config: StravaAppConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Save Strava app credentials for the current user.

    Each user can configure their own Strava application credentials.
    This allows each family member to connect their own Strava account.

    Requires authentication.
    """
    try:
        strava_service.save_strava_app_config(
            user_id=current_user.id,
            client_id=config.client_id,
            client_secret=config.client_secret,
            db_session=db
        )
        return {"message": "Strava app credentials saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save Strava config: {str(e)}"
        )


@router.get("/authorize", response_model=StravaAuthUrlResponse)
async def get_strava_authorization_url(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate Strava OAuth2 authorization URL.

    Returns the URL to redirect the user to for Strava authorization.
    The user will be prompted to authorize the app to access their activity data.

    Requires authentication and configured Strava app credentials.
    """
    try:
        # Get user's Strava app credentials
        config = strava_service.get_strava_app_config(current_user.id, db)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please configure your Strava app credentials first"
            )

        # Always use the backend callback URL - frontend's redirect_uri is ignored
        # The OAuth flow: Frontend → Backend (get auth URL) → Strava → Backend (callback) → Frontend
        uri = settings.strava_redirect_uri

        # Generate a simple state for CSRF protection
        state = f"{current_user.id}_{int(datetime.utcnow().timestamp())}"

        auth_url = strava_service.get_authorization_url(config["client_id"], uri, state)

        return StravaAuthUrlResponse(authorization_url=auth_url)

    except HTTPException:
        raise
    except strava_service.StravaAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strava configuration error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating authorization URL: {str(e)}"
        )


@router.post("/callback", response_model=StravaConnectionResponse)
async def strava_oauth_callback(
    callback_data: StravaCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Handle Strava OAuth2 callback.

    Exchanges the authorization code for access and refresh tokens,
    and stores the connection for the authenticated user.

    Requires authentication and configured Strava app credentials.
    """
    try:
        # Get user's Strava app credentials
        config = strava_service.get_strava_app_config(current_user.id, db)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strava app credentials not configured"
            )

        # Exchange code for tokens
        token_response = strava_service.exchange_code_for_token(
            config["client_id"],
            config["client_secret"],
            callback_data.code
        )

        # Extract athlete info from token response
        athlete_data = token_response.get("athlete", {})

        # Save connection
        connection = strava_service.save_strava_connection(
            user_id=current_user.id,
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=token_response["expires_at"],
            athlete_data=athlete_data,
            db_session=db
        )

        return StravaConnectionResponse(
            connected=True,
            athlete_name=connection.strava_athlete_name,
            athlete_id=connection.strava_athlete_id,
            athlete_profile=connection.strava_athlete_profile,
            created_at=connection.created_at,
            last_sync_at=connection.last_sync_at,
            sync_status=connection.sync_status
        )

    except HTTPException:
        raise
    except strava_service.StravaAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Strava authentication failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing Strava callback: {str(e)}"
        )


@router.get("/connection", response_model=StravaConnectionResponse)
async def get_strava_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's Strava connection status.

    Returns information about user's Strava connection, including
    whether it's active, athlete info, last sync time, and any error status.

    Requires authentication.
    """
    connection = db.query(StravaConnection).filter(
        StravaConnection.user_id == current_user.id
    ).first()

    if not connection:
        return StravaConnectionResponse(
            connected=False,
            athlete_name=None,
            athlete_id=None,
            athlete_profile=None,
            created_at=None,
            last_sync_at=None,
            sync_status="not_connected"
        )

    # If only config is set but not OAuth tokens, return not_connected
    if connection.sync_status == "config_set":
        return StravaConnectionResponse(
            connected=False,
            athlete_name=None,
            athlete_id=None,
            athlete_profile=None,
            created_at=connection.created_at,
            last_sync_at=None,
            sync_status="not_connected"
        )

    return StravaConnectionResponse(
        connected=connection.sync_status == "connected",
        athlete_name=connection.strava_athlete_name,
        athlete_id=connection.strava_athlete_id,
        athlete_profile=connection.strava_athlete_profile,
        created_at=connection.created_at,
        last_sync_at=connection.last_sync_at,
        sync_status=connection.sync_status
    )


@router.delete("/connection")
async def unlink_strava(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Unlink user's Strava account.

    Removes the stored OAuth tokens and connection data.
    Activity metrics that were previously synced remain in the database.

    Requires authentication.
    """
    strava_service.delete_strava_connection(current_user.id, db_session=db)

    return {"message": "Strava account unlinked successfully"}


@router.post("/sync", response_model=StravaSyncResponse)
async def sync_strava(
    sync_request: StravaSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger manual Strava data sync.

    Fetches activities from Strava for the specified date range
    and updates the user's activity and health metrics.

    Requires authentication and an active Strava connection.
    """
    try:
        results = strava_service.refresh_strava_data(
            user_id=current_user.id,
            days=sync_request.days,
            db_session=db
        )

        return StravaSyncResponse(
            success=results['success'],
            activities_synced=results['activities_synced'],
            metrics_updated=results['metrics_updated'],
            errors=results['errors'],
            last_sync_at=results.get('last_sync_at')
        )

    except strava_service.StravaAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Strava authentication failed: {str(e)}"
        )
    except strava_service.StravaAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Strava API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing Strava data: {str(e)}"
        )


@router.get("/activities", response_model=StravaActivitiesResponse)
async def get_activities(
    start_date: Optional[date_type] = Query(None, description="Filter activities from this date"),
    end_date: Optional[date_type] = Query(None, description="Filter activities to this date"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of activities to return"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (e.g., Run, Ride)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get Strava activities for the current user.

    Returns a list of synced Strava activities, optionally filtered
    by date range and activity type.

    Requires authentication.
    """
    from datetime import datetime

    query = db.query(ActivityMetric).filter(
        ActivityMetric.user_id == current_user.id
    )

    if start_date:
        query = query.filter(ActivityMetric.date >= start_date)
    if end_date:
        query = query.filter(ActivityMetric.date <= end_date)
    if activity_type:
        query = query.filter(ActivityMetric.activity_type == activity_type)

    query = query.order_by(ActivityMetric.date.desc(), ActivityMetric.start_date.desc())
    query = query.limit(limit)

    activities = query.all()

    return StravaActivitiesResponse(
        activities=[StravaActivityResponse.model_validate(a) for a in activities],
        count=len(activities)
    )


@router.get("/activities/{activity_id}", response_model=StravaActivityResponse)
async def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific Strava activity by ID.

    Returns detailed information about a single synced Strava activity.

    Requires authentication.
    """
    activity = db.query(ActivityMetric).filter(
        ActivityMetric.id == activity_id,
        ActivityMetric.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    return StravaActivityResponse.model_validate(activity)
