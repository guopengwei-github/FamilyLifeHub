# ABOUTME: Garmin Connect API endpoints for OAuth authentication and data sync
# ABOUTME: Handles username/password login, MFA verification, connection status, and sync triggers
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import secrets
import base64
import json

from app.core.database import get_db
from app.core.security import get_current_active_user, check_rate_limit
from app.models import User, GarminConnection
from app.services import garmin as garmin_service
from app.schemas import (
    GarminLoginRequest,
    GarminMfaVerifyRequest,
    GarminConnectionResponse,
    GarminSyncRequest,
    GarminSyncResponse
)

router = APIRouter(prefix="/garmin", tags=["Garmin"])


# Rate limiting: 10 requests per minute for auth endpoints
def rate_limit_auth(user: User = Depends(get_current_active_user)):
    """Rate limit dependency for Garmin auth endpoints."""
    rate_key = f"garmin_auth:{user.id}"
    allowed, retry_after = check_rate_limit(rate_key, max_requests=10, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


@router.post("/test-credentials")
async def test_garmin_credentials(
    login_data: GarminLoginRequest,
    current_user: User = Depends(get_current_active_user),
    _rate_limit: None = Depends(rate_limit_auth)
):
    """
    Test Garmin credentials without storing them.

    Requires authentication.
    """
    try:
        is_valid = garmin_service.test_garmin_credentials(
            login_data.username,
            login_data.password,
            login_data.mfa_token,
            login_data.is_cn
        )

        return {
            "valid": is_valid,
            "error": None if is_valid else "Invalid credentials or MFA required",
            "region": "Garmin China (garmin.cn)" if login_data.is_cn else "Garmin International (garmin.com)"
        }
    except garmin_service.GarminAuthError as e:
        error_msg = str(e)
        return {
            "valid": False,
            "error": error_msg,
            "region": "Garmin China (garmin.cn)" if login_data.is_cn else "Garmin International (garmin.com)"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing credentials: {str(e)}"
        )


@router.post("/mfa/verify", response_model=GarminConnectionResponse)
async def verify_garmin_mfa(
    mfa_data: GarminMfaVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _rate_limit: None = Depends(rate_limit_auth)
):
    """
    Complete Garmin MFA login (second step).

    This endpoint only requires MFA token and session ID - no username/password needed.
    The Client object is retrieved from server-side session storage.

    Requires authentication.

    Flow:
    1. First call POST /api/v1/garmin/connect with username/password
    2. If MFA required, get session_id from error response
    3. Call this endpoint with mfa_token and mfa_session_id
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Resume MFA login using stored session
        # Returns client, user_info, is_cn, username, password
        client, user_info, is_cn, username, password = garmin_service.resume_mfa_login(
            mfa_data.mfa_token,
            mfa_data.mfa_session_id
        )

        # Save connection with OAuth tokens and credentials from session
        connection = garmin_service.save_garmin_connection(
            user_id=current_user.id,
            username=username,
            password=password,
            mfa_token=mfa_data.mfa_token,
            garmin_user_id=user_info.get('garmin_user_id'),
            garmin_display_name=user_info.get('garmin_display_name'),
            is_cn=is_cn,
            client=client,
            db_session=db
        )

        return GarminConnectionResponse(
            connected=True,
            garmin_display_name=connection.garmin_display_name,
            garmin_user_id=connection.garmin_user_id,
            created_at=connection.created_at,
            last_sync_at=connection.last_sync_at,
            sync_status=connection.sync_status
        )

    except garmin_service.GarminAuthError as e:
        error_detail = str(e)
        # MFA-specific error handling
        if "expired" in error_detail.lower() or "not found" in error_detail.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )
        if "Invalid verification code" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_detail
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Garmin MFA verification failed: {error_detail}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying Garmin MFA: {str(e)}"
        )


@router.post("/connect", response_model=GarminConnectionResponse)
async def connect_garmin(
    login_data: GarminLoginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _rate_limit: None = Depends(rate_limit_auth)
):
    """
    Connect to Garmin Connect using username/password.

    Validates credentials and stores encrypted connection information.
    If MFA is required, the user will need to provide an MFA token.
    OAuth tokens are extracted and stored after successful login for future use.

    Requires authentication.

    MFA Flow:
    1. First request with username/password: Returns MFA_REQUIRED:<session_id>
    2. Second request with mfa_token + mfa_session_id: Completes login
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Perform login
        # If MFA is detected, service layer raises GarminAuthError with MFA_REQUIRED:<session_id>
        client, user_info = garmin_service.login(
            login_data.username,
            login_data.password,
            login_data.mfa_token,
            login_data.is_cn,
            mfa_session_id=login_data.mfa_session_id
        )

        # Save connection with OAuth tokens
        connection = garmin_service.save_garmin_connection(
            user_id=current_user.id,
            username=login_data.username,
            password=login_data.password,
            mfa_token=login_data.mfa_token,
            garmin_user_id=user_info.get('garmin_user_id'),
            garmin_display_name=user_info.get('garmin_display_name'),
            is_cn=login_data.is_cn,
            client=client,
            db_session=db
        )

        return GarminConnectionResponse(
            connected=True,
            garmin_display_name=connection.garmin_display_name,
            garmin_user_id=connection.garmin_user_id,
            created_at=connection.created_at,
            last_sync_at=connection.last_sync_at,
            sync_status=connection.sync_status
        )

    except garmin_service.GarminAuthError as e:
        error_detail = str(e)
        logger.info(f"GarminAuthError caught: {error_detail[:100]}")
        # Check if this is our MFA_REQUIRED error with session_id
        if error_detail.startswith("MFA_REQUIRED:"):
            # The service layer now returns a session_id
            # Pass this through to the frontend
            mfa_session_id = error_detail.split("MFA_REQUIRED:", 1)[1]
            logger.info(f"MFA_REQUIRED with session_id detected: {mfa_session_id[:16]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MFA_REQUIRED:{mfa_session_id}"
            )
        # Preserve detailed error messages from the service layer
        # Don't overwrite with generic messages
        if "Garmin China authentication is not fully supported" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )
        # Check if error indicates MFA is required (without session_id)
        if error_detail == "MFA_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your Garmin account requires 2FA. Please enable the MFA option and enter your authentication code."
            )
        # Check for MFA session errors
        if "MFA session" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )
        if "401" in error_detail or "Unauthorized" in error_detail:
            error_detail = "Invalid Garmin credentials. Please verify your username and password. If you have 2FA enabled, you may need to provide an MFA token."
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Garmin authentication failed: {error_detail}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error connecting to Garmin: {str(e)}"
        )


@router.get("/connection", response_model=GarminConnectionResponse)
async def get_garmin_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's Garmin connection status.

    Returns information about user's Garmin connection, including
    whether it's active, last sync time, and any error status.

    Requires authentication.
    """
    connection = db.query(GarminConnection).filter(
        GarminConnection.user_id == current_user.id
    ).first()

    if not connection:
        return GarminConnectionResponse(
            connected=False,
            garmin_display_name=None,
            garmin_user_id=None,
            created_at=None,  # type: ignore
            last_sync_at=None,
            sync_status="not_connected"
        )

    return GarminConnectionResponse(
        connected=connection.sync_status == "connected",
        garmin_display_name=connection.garmin_display_name,
        garmin_user_id=connection.garmin_user_id,
        created_at=connection.created_at,
        last_sync_at=connection.last_sync_at,
        sync_status=connection.sync_status
    )


@router.delete("/connection")
async def unlink_garmin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Unlink user's Garmin account.

    Removes the stored credentials and connection data.

    Requires authentication.
    """
    connection = db.query(GarminConnection).filter(
        GarminConnection.user_id == current_user.id
    ).first()

    if connection:
        db.delete(connection)
        db.commit()

    return {"message": "Garmin account unlinked successfully"}


@router.post("/sync", response_model=GarminSyncResponse)
async def sync_garmin(
    sync_request: GarminSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger manual Garmin data sync.

    Fetches health metrics from Garmin Connect for the specified
    date range and updates the user's health data.

    Requires authentication and an active Garmin connection.
    """
    try:
        results = garmin_service.refresh_garmin_data(
            user_id=current_user.id,
            days=sync_request.days,
            db_session=db
        )

        return GarminSyncResponse(
            success=results['success'],
            days_synced=results['days_synced'],
            metrics_created=results['metrics_created'],
            metrics_updated=results['metrics_updated'],
            errors=results['errors'],
            last_sync_at=results.get('last_sync_at')
        )

    except garmin_service.GarminAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Garmin authentication failed: {str(e)}"
        )
    except garmin_service.GarminAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Garmin API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing Garmin data: {str(e)}"
        )
