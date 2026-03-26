"""
ABOUTME: Email service for sending health report notifications.
ABOUTME: Supports SMTP with SSL/TLS for secure email delivery.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from app.models.smtp_config import SmtpConfig
from app.models import User

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""

    @staticmethod
    def send_email(
        smtp_config: SmtpConfig,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Send an email using SMTP configuration.

        Args:
            smtp_config: SmtpConfig model instance
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{smtp_config.sender_name or smtp_config.smtp_user} <{smtp_config.sender_email or smtp_config.smtp_user}>"
            msg['To'] = to_email
            msg['Date'] = formatdate(localtime=True)

            # Add plain text part if provided
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

            # Add HTML part
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Connect and send
            if smtp_config.use_ssl:
                # SSL connection (port 465 typically)
                with smtplib.SMTP_SSL(smtp_config.smtp_host, smtp_config.smtp_port, timeout=30) as server:
                    server.login(smtp_config.smtp_user, smtp_config.smtp_password)
                    server.sendmail(
                        smtp_config.sender_email or smtp_config.smtp_user,
                        to_email,
                        msg.as_string()
                    )
            else:
                # STARTTLS connection (port 587 typically)
                with smtplib.SMTP(smtp_config.smtp_host, smtp_config.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(smtp_config.smtp_user, smtp_config.smtp_password)
                    server.sendmail(
                        smtp_config.sender_email or smtp_config.smtp_user,
                        to_email,
                        msg.as_string()
                    )

            logger.info(f"Email sent successfully to {to_email}")
            return True, "Email sent successfully"

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def test_connection(smtp_config: SmtpConfig) -> Tuple[bool, str]:
        """
        Test SMTP connection without sending email.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if smtp_config.use_ssl:
                with smtplib.SMTP_SSL(smtp_config.smtp_host, smtp_config.smtp_port, timeout=10) as server:
                    server.login(smtp_config.smtp_user, smtp_config.smtp_password)
            else:
                with smtplib.SMTP(smtp_config.smtp_host, smtp_config.smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_config.smtp_user, smtp_config.smtp_password)

            return True, "SMTP connection successful"
        except smtplib.SMTPAuthenticationError:
            return False, "认证失败，请检查用户名和密码"
        except smtplib.SMTPConnectError:
            return False, f"无法连接到 {smtp_config.smtp_host}:{smtp_config.smtp_port}"
        except Exception as e:
            return False, f"连接测试失败: {str(e)}"

    @staticmethod
    def send_report_notification(
        db: Session,
        user_id: int,
        report_type: str,
        report_date: str,
        report_content: str
    ) -> Tuple[bool, str]:
        """
        Send a health report notification email to a user.

        Args:
            db: Database session
            user_id: User ID to send to
            report_type: 'morning' or 'evening'
            report_date: Date string YYYY-MM-DD
            report_content: Markdown report content

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, f"User {user_id} not found"

        # Check notification email
        to_email = user.mail_for_notification
        if not to_email:
            return False, f"User {user_id} has no notification email configured"

        # Get SMTP config
        smtp_config = db.query(SmtpConfig).filter(
            SmtpConfig.user_id == user_id,
            SmtpConfig.is_active == 1
        ).first()
        if not smtp_config:
            return False, f"User {user_id} has no active SMTP configuration"

        # Generate email content
        report_type_cn = "晨间报告" if report_type == "morning" else "晚间报告"
        subject = f"【{report_type_cn}】{user.name} - {report_date}"

        html_content = EmailService._markdown_to_email_html(
            report_content,
            title=f"{user.name}的{report_type_cn}",
            date=report_date
        )

        return EmailService.send_email(
            smtp_config=smtp_config,
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=report_content
        )

    @staticmethod
    def _markdown_to_email_html(markdown_content: str, title: str, date: str) -> str:
        """
        Convert markdown content to styled HTML email.
        """
        # Simple markdown to HTML conversion
        html_body = markdown_content

        # Convert headers
        import re
        html_body = re.sub(r'^### (.*?)$', r'<h3 style="color: #4a5568; margin-top: 20px;">\1</h3>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^## (.*?)$', r'<h2 style="color: #2d3748; margin-top: 24px;">\1</h2>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^# (.*?)$', r'<h1 style="color: #1a202c;">\1</h1>', html_body, flags=re.MULTILINE)

        # Convert bold
        html_body = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_body)

        # Convert lists
        html_body = re.sub(r'^- (.*?)$', r'<li style="margin-left: 20px;">\1</li>', html_body, flags=re.MULTILINE)

        # Convert paragraphs (lines separated by blank lines)
        html_body = re.sub(r'\n\n', r'</p><p style="margin: 12px 0;">', html_body)
        html_body = f'<p style="margin: 12px 0;">{html_body}</p>'

        # Wrap in email template
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 24px;">{title}</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">{date}</p>
    </div>
    <div style="background: #ffffff; padding: 24px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px;">
        {html_body}
    </div>
    <div style="text-align: center; margin-top: 20px; color: #718096; font-size: 12px;">
        <p>此邮件由 FamilyLifeHub 自动发送</p>
    </div>
</body>
</html>
        """.strip()

    @staticmethod
    def send_data_expired_notification(
        db: Session,
        user: User,
        last_update: datetime,
        report_type: str,
        retry_count: int,
        max_retries: int = 3
    ) -> Tuple[bool, str]:
        """
        发送数据过期提醒邮件给用户

        Args:
            db: Database session
            user: User对象
            last_update: 最后更新时间（本地时间）
            report_type: 'morning' or 'evening'
            retry_count: 当前重试次数（从1开始）
            max_retries: 最大重试次数

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Get SMTP config
        smtp_config = db.query(SmtpConfig).filter(
            SmtpConfig.user_id == user.id,
            SmtpConfig.is_active == 1
        ).first()
        
        if not smtp_config:
            return False, f"User {user.id} has no active SMTP configuration"
        
        # Generate email content
        report_type_cn = "晨间报告" if report_type == "morning" else "晚间报告"
        subject = f"【数据过期提醒】请更新 Garmin 数据 - 第 {retry_count}/{max_retries} 次重试"
        
        # 格式化时间
        last_update_local = last_update.strftime('%Y-%m-%d %H:%M:%S')
        now_local = datetime.now(timezone.utc) + timedelta(hours=8)
        
        # 生成HTML邮件内容
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #f09300 0%, #f09b4b 100%); color: white; padding: 24px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 24px;">数据过期提醒</h1>
    </div>
    <div style="background: #fff9e6; padding: 24px; border: 1px solid #f3f4f7; border-top: none; border-radius: 0 0 8px 8px;">
        <p style="color: #2d3748; margin-bottom: 16px;">
            亲爱的 {user.name}：
        </p>
        
        <p style="color: #4a5568; margin-bottom: 12px;">
            检测到您的 Garmin 数据已超过 <strong>{DATA_FRESHNESS_THRESHOLD_HOURS}</strong> 小时未更新。
        </p>
        
        <p style="color: #4a5568; margin-bottom: 16px;">
            系统检测到数据过期，会在 <strong>{RETRY_INTERVAL_MINUTES}</strong> 分钟后自动重试（最多 {max_retries} 次）。
        </p>
        
        <h3 style="color: #2d3748; margin-top: 24px;">最后更新时间</h3>
        <p style="margin-left: 20px; margin-bottom: 16px;">
            <strong>更新时间（北京时间）：</strong> {last_update_local}
        </p>
        
        <h3 style="color: #2d3748; margin-top: 24px;">操作指引</h3>
        <ul style="margin-left: 20px; color: #4a5568;">
            <li style="margin-bottom: 8px;">打开 Garmin Connect App</li>
            <li style="margin-bottom: 8px;">下拉同步数据（约 5-10 分钟）等待数据上传到服务端</li>
            <li style="margin-bottom: 8px;">确保手机蓝牙已开启</li>
            <li style="margin-bottom: 8px;">确保 Garmin Connect App 正常运行</li>
        </ul>
        
        <h3 style="color: #2d3748; margin-top: 24px;">重试进度</h3>
        <p style="margin-top: 20px; color: #718096; font-size: 12px; text-align: center;">
            第 {retry_count}/{max_retries} 次重试
        </p>
        
        <p style="text-align: center; margin-top: 20px; color: #718096; font-size: 12px;">
            此邮件由 FamilyLifeHub 自动发送
        </p>
    </div>
</body>
</html>
        """.strip()
        
        # 发送邮件
        return EmailService.send_email(
            smtp_config=smtp_config,
            to_email=user.mail_for_notification,
            subject=subject,
            html_content=html_content
        )
