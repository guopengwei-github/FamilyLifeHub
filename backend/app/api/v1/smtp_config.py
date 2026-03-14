"""
ABOUTME: SMTP configuration API endpoints for email notification settings.
ABOUTME: Allows users to configure and test SMTP settings for sending reports.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.models.smtp_config import SmtpConfig
from app.schemas import (
    SmtpConfigCreate,
    SmtpConfigUpdate,
    SmtpConfigResponse,
    SmtpTestResponse,
    UserNotificationSettingsUpdate,
    UserNotificationSettingsResponse
)
from app.services.email_service import EmailService

router = APIRouter()


@router.get("/smtp-config", response_model=SmtpConfigResponse)
def get_smtp_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's SMTP configuration.

    Returns the SMTP config with password masked.
    """
    config = db.query(SmtpConfig).filter(SmtpConfig.user_id == current_user.id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    return config


@router.post("/smtp-config", response_model=SmtpConfigResponse)
def create_smtp_config(
    config_data: SmtpConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create SMTP configuration for the current user.

    If configuration already exists, returns 400 error.
    Use PUT to update existing configuration.
    """
    # Check if config already exists
    existing = db.query(SmtpConfig).filter(SmtpConfig.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="SMTP configuration already exists. Use PUT to update.")

    # Create new config
    config = SmtpConfig(
        user_id=current_user.id,
        smtp_host=config_data.smtp_host,
        smtp_port=config_data.smtp_port,
        smtp_user=config_data.smtp_user,
        smtp_password=config_data.smtp_password,
        use_ssl=config_data.use_ssl,
        sender_email=config_data.sender_email,
        sender_name=config_data.sender_name,
        is_active=1
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    return config


@router.put("/smtp-config", response_model=SmtpConfigResponse)
def update_smtp_config(
    config_data: SmtpConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update SMTP configuration for the current user.

    Creates configuration if it doesn't exist.
    """
    config = db.query(SmtpConfig).filter(SmtpConfig.user_id == current_user.id).first()

    if not config:
        # Create new config with provided data
        if not config_data.smtp_host or not config_data.smtp_user or not config_data.smtp_password:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields for new configuration: smtp_host, smtp_user, smtp_password"
            )

        config = SmtpConfig(
            user_id=current_user.id,
            smtp_host=config_data.smtp_host,
            smtp_port=config_data.smtp_port or 465,
            smtp_user=config_data.smtp_user,
            smtp_password=config_data.smtp_password,
            use_ssl=config_data.use_ssl if config_data.use_ssl is not None else 1,
            sender_email=config_data.sender_email,
            sender_name=config_data.sender_name,
            is_active=config_data.is_active if config_data.is_active is not None else 1
        )
        db.add(config)
    else:
        # Update existing config
        update_data = config_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)

    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)

    return config


@router.delete("/smtp-config")
def delete_smtp_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete SMTP configuration for the current user.
    """
    config = db.query(SmtpConfig).filter(SmtpConfig.user_id == current_user.id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    db.delete(config)
    db.commit()

    return {"message": "SMTP configuration deleted"}


@router.post("/smtp-config/test", response_model=SmtpTestResponse)
def test_smtp_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test SMTP connection using the current user's configuration.

    Sends a test connection without actually sending an email.
    """
    config = db.query(SmtpConfig).filter(SmtpConfig.user_id == current_user.id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SMTP configuration not found")

    success, message = EmailService.test_connection(config)

    # Update test status
    config.last_test_at = datetime.now(timezone.utc)
    config.last_test_status = "success" if success else "failed"
    if not success:
        config.last_error = message
    else:
        config.last_error = None
    db.commit()

    return SmtpTestResponse(success=success, message=message)


# ============ User Notification Settings ============

@router.get("/notification-settings", response_model=UserNotificationSettingsResponse)
def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's notification settings.

    Returns the email address used for notifications.
    """
    return UserNotificationSettingsResponse(
        mail_for_notification=current_user.mail_for_notification
    )


@router.put("/notification-settings", response_model=UserNotificationSettingsResponse)
def update_notification_settings(
    settings: UserNotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's notification settings.

    Sets the email address for receiving report notifications.
    """
    if settings.mail_for_notification is not None:
        current_user.mail_for_notification = settings.mail_for_notification
        db.commit()
        db.refresh(current_user)

    return UserNotificationSettingsResponse(
        mail_for_notification=current_user.mail_for_notification
    )
