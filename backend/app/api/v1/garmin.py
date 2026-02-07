"""
Garmin Connect API endpoints.
Handles username/password authentication and data synchronization for Garmin Connect.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, GarminConnection
from app.services import garmin as garmin_service
from app.schemas import (
    GarminLoginRequest,
    GarminConnectionResponse,
    GarminSyncRequest,
    GarminSyncResponse
)

router = APIRouter(prefix="/garmin", tags=["Garmin"])


@router.post("/test-credentials")
async def test_garmin_credentials(
    login_data: GarminLoginRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test Garmin credentials without storing them.
    Useful for troubleshooting connection issues.

    Requires authentication.
    """
    try:
        is_valid = garmin_service.test_garmin_credentials(
            login_data.username,
            login_data.password,
            login_data.mfa_token,
            login_data.is_cn
        )

        error_msg = garmin_service.get_last_login_error()

        return {
            "valid": is_valid,
            "error": error_msg if not is_valid else None,
            "region": "Garmin China (garmin.cn)" if login_data.is_cn else "Garmin International (garmin.com)"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing credentials: {str(e)}"
        )


@router.post("/connect", response_model=GarminConnectionResponse)
async def connect_garmin(
    login_data: GarminLoginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Connect to Garmin Connect using username/password.

    Validates credentials and stores encrypted connection information.
    If MFA is required, the user will need to provide an MFA token.
    OAuth tokens are extracted and stored after successful login for future use.

    Requires authentication.
    """
    garmin_client = None
    try:
        # Perform a single login to validate credentials and get the client
        # This client will have the OAuth tokens we need to serialize
        garmin_client = garmin_service.login(
            login_data.username,
            login_data.password,
            login_data.mfa_token,
            login_data.is_cn
        )

        # Fetch user profile to get display name
        garmin_user_id = None
        garmin_display_name = None

        try:
            profile = garmin_client.get_user_profile()
            if profile:
                garmin_user_id = profile.get("userProfileId")
                if "userDisplayName" in profile:
                    garmin_display_name = profile["userDisplayName"]
                elif "fullName" in profile:
                    garmin_display_name = profile["fullName"]
        except Exception as e:
            # Profile fetch failed, but credentials are valid - continue anyway
            pass

        # Save connection with OAuth tokens from the authenticated client
        connection = garmin_service.save_garmin_connection(
            user_id=current_user.id,
            username=login_data.username,
            password=login_data.password,
            mfa_token=login_data.mfa_token,  # May be None - OAuth tokens will be used instead
            garmin_user_id=garmin_user_id,
            garmin_display_name=garmin_display_name,
            is_cn=login_data.is_cn,
            garmin_client=garmin_client,  # Pass client to extract OAuth tokens
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
        # Check if error indicates MFA is required
        if "MFA" in error_detail or "2FA" in error_detail or "OTP" in error_detail or "authenticator" in error_detail.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your Garmin account requires 2FA. Please enable the MFA option and enter your authentication code."
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
