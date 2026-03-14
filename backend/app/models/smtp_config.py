"""
ABOUTME: SMTP configuration model for email notifications.
ABOUTME: Stores SMTP server settings per user for sending reports.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class SmtpConfig(Base):
    """
    SMTP configuration for sending email notifications.
    Each user can have their own SMTP settings.
    """
    __tablename__ = "smtp_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # SMTP server settings
    smtp_host = Column(String(255), nullable=False)  # e.g., 'smtp.qq.com'
    smtp_port = Column(Integer, default=465, nullable=False)
    smtp_user = Column(String(255), nullable=False)  # SMTP login username
    smtp_password = Column(Text, nullable=False)  # Encrypted SMTP password or app token
    use_ssl = Column(Integer, default=1, nullable=False)  # 1=SSL/TLS, 0=STARTTLS

    # Sender info
    sender_email = Column(String(255), nullable=True)  # Sender display email
    sender_name = Column(String(100), nullable=True)  # Sender display name

    # Status
    is_active = Column(Integer, default=1, nullable=False)  # 1=enabled, 0=disabled
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=True)  # 'success', 'failed'
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="smtp_config")

    def __repr__(self):
        return f"<SmtpConfig(user_id={self.user_id}, host={self.smtp_host})>"
