"""
Agent API for external automation systems.

Provides HTTP endpoints for Prometheus Agent to trigger:
- Garmin data sync
- Health report generation
- Email notifications
- Complete workflows (morning/evening reports)
"""
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from app.core.database import get_db, SessionLocal
from app.core.security import verify_agent_api_key
from app.models import User, HealthReport
from app.services import garmin as garmin_service
from app.services.report_generator import generate_morning_report, generate_evening_report
from app.services.email_service import EmailService
from app.services.llm.zhipu import ZhipuProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


# Request/Response Models
class SyncDataRequest(BaseModel):
    user_id: Optional[int] = None
    days: int = 1


class GenerateReportRequest(BaseModel):
    user_id: int
    report_type: str
    report_date: Optional[date] = None


class SendEmailRequest(BaseModel):
    user_id: int
    report_type: str
    custom_content: Optional[str] = None


class WorkflowRequest(BaseModel):
    user_ids: Optional[List[int]] = None
class SyncDataResponse(BaseModel):
    success: bool
    user_id: Optional[int] = None
    days_synced: int = 0
    metrics_created: int = 0
    metrics_updated: int = 0
    errors: List[str] = []
class GenerateReportResponse(BaseModel):
    success: bool
    user_id: int
    report_type: str
    report_date: date
    content: str
    errors: List[str] = []
class SendEmailResponse(BaseModel):
    success: bool
    user_id: int
    message: str
    errors: List[str] = []
class WorkflowResponse(BaseModel):
    success: bool
    results: Dict[str, Any]
    errors: List[str] = []
# Helper functions
def get_llm_provider() -> ZhipuProvider:
    return ZhipuProvider(
        api_key=settings.zhipu_api_key,
        model=settings.zhipu_model,
        base_url=settings.zhipu_base_url
    )
async def _sync_user_data(user_id: int, db: Session) -> Dict[str, Any]:
    """Sync Garmin data for a specific user."""
    try:
        results = garmin_service.refresh_garmin_data(
            user_id=user_id,
            days=1,
            db_session=db
        )
        return {
            "success": True,
            "user_id": user_id,
            "days_synced": results["days_synced"],
            "metrics_created": results["metrics_created"],
            "metrics_updated": results["metrics_updated"],
            "errors": results.get("errors", [])
        }
    except Exception as e:
        logger.error(f"Garmin sync failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "errors": [str(e)],
            "days_synced": 0,
            "metrics_created": 0,
            "metrics_updated": 0
        }
async def _generate_user_report(
    user_id: int,
    report_type: str,
    db: Session
) -> Dict[str, Any]:
    """Generate a health report for a user."""
    try:
        report_date = date.today()
        llm_provider = get_llm_provider()
        
        if report_type == "morning":
            report_data = await generate_morning_report(
                db=db,
                user_id=user_id,
                report_date=report_date,
                llm_provider=llm_provider
            )
        else:
            report_data = await generate_evening_report(
                db=db,
                user_id=user_id,
                report_date=report_date,
                llm_provider=llm_provider
            )
        
        return {
            "success": True,
            "user_id": user_id,
            "report_type": report_type,
            "report_date": report_date,
            "content": report_data["content"],
            "errors": []
        }
    except Exception as e:
        logger.error(f"Report generation failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "report_type": report_type,
            "errors": [str(e)],
            "report_date": report_date,
            "content": ""
        }
async def _send_user_email(
    user_id: int,
    report_type: str,
    custom_content: Optional[str],
    db: Session
) -> Dict[str, Any]:
    """Send email notification for a user."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "user_id": user_id,
                "message": "User not found",
                "errors": ["User not found"]
            }
        
        if not user.mail_for_notification:
            return {
                "success": False,
                "user_id": user_id,
                "message": "User has no notification email configured",
                "errors": ["No notification email"]
            }
        
        # Get SMTP config
        from app.models.smtp_config import SmtpConfig
        smtp_config = db.query(SmtpConfig).filter(
            SmtpConfig.user_id == user_id,
            SmtpConfig.is_active == 1
        ).first()
        
        if not smtp_config:
            return {
                "success": False,
                "user_id": user_id,
                "message": "User has no active SMTP configuration",
                "errors": ["No SMTP configuration"]
            }
        
        # Generate report if not provided
        report_content = custom_content
        if not report_content:
            report = db.query(HealthReport).filter(
                HealthReport.user_id == user_id,
                HealthReport.report_date == date.today(),
                HealthReport.report_type == report_type
            ).first()
            
            if not report:
                return {
                    "success": False,
                    "user_id": user_id,
                    "message": f"No {report_type} report found for today",
                    "errors": [f"No {report_type} report found"]
                }
            
            report_content = report.content
        
        # Send email
        success, message = EmailService.send_report_notification(
            db=db,
            user_id=user_id,
            report_type=report_type,
            report_date=str(date.today()),
            report_content=report_content
        )
        
        return {
            "success": success,
            "user_id": user_id,
            "message": message,
            "errors": []
        }
    except Exception as e:
        logger.error(f"Email sending failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "message": str(e),
            "errors": [str(e)]
        }
async def _execute_morning_workflow(user_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """Execute complete morning workflow for all or specified users."""
    results = {
        "sync": [],
        "reports": [],
        "emails": [],
        "errors": []
    }
    
    db = SessionLocal()
    try:
        if user_ids is None:
            users_list = db.query(User).filter(User.is_active == 1).all()
        else:
            users_list = db.query(User).filter(
                User.is_active == 1,
                User.id.in_(user_ids)
            ).all()
        
        for user in users_list:
            # Sync data
            sync_result = await _sync_user_data(user.id, db)
            results["sync"].append(sync_result)
            
            # Generate report
            if sync_result["success"]:
                report_result = await _generate_user_report(
                    user_id=user.id,
                    report_type="morning",
                    db=db
                )
                results["reports"].append(report_result)
                
                # Send email
                if report_result["success"]:
                    email_result = await _send_user_email(
                        user_id=user.id,
                        report_type="morning",
                        db=db
                    )
                    results["emails"].append(email_result)
                else:
                    results["errors"].append(f"Email failed for user {user.id}")
            else:
                results["errors"].append(f"Report generation failed for user {user.id}")
    finally:
        db.close()
    
    return {
        "success": True,
        "results": results
    }
async def _execute_evening_workflow(user_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """Execute complete evening workflow for all or specified users."""
    results = {
        "sync": [],
        "reports": [],
        "emails": [],
        "errors": []
    }
    
    db = SessionLocal()
    try:
        if user_ids is None:
            users_list = db.query(User).filter(User.is_active == 1).all()
        else:
            users_list = db.query(User).filter(
                User.is_active == 1,
                User.id.in_(user_ids)
            ).all()
        
        for user in users_list:
            # Sync data
            sync_result = await _sync_user_data(user.id, db)
            results["sync"].append(sync_result)
            
            # Generate report
            if sync_result["success"]:
                report_result = await _generate_user_report(
                    user_id=user.id,
                    report_type="evening",
                    db=db
                )
                results["reports"].append(report_result)
                
                # Send email
                if report_result["success"]:
                    email_result = await _send_user_email(
                        user_id=user.id,
                        report_type="evening",
                        db=db
                    )
                    results["emails"].append(email_result)
                else:
                    results["errors"].append(f"Email failed for user {user.id}")
            else:
                results["errors"].append(f"Report generation failed for user {user.id}")
    finally:
        db.close()
    
    return {
        "success": True,
        "results": results
    }
# API Endpoints
@router.post("/sync-data", response_model=SyncDataResponse)
async def sync_data(
    request: SyncDataRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_api_key)
):
    """Sync Garmin data for one or all users."""
    try:
        if request.user_id:
            # Sync specific user
            result = await _sync_user_data(request.user_id, db)
            return SyncDataResponse(
                success=result["success"],
                user_id=result["user_id"],
                days_synced=result["days_synced"],
                metrics_created=result["metrics_created"],
                metrics_updated=result["metrics_updated"],
                errors=result["errors"]
            )
        else:
            # Sync all users
            users = db.query(User).filter(User.is_active == 1).all()
            results_list = []
            for user in users:
                result = await _sync_user_data(user.id, db)
                results_list.append(result)
            
            return SyncDataResponse(
                success=all(r["success"] for r in results_list),
                user_id=None,
                days_synced=sum(r["days_synced"] for r in results_list),
                metrics_created=sum(r["metrics_created"] for r in results_list),
                metrics_updated=sum(r["metrics_updated"] for r in results_list),
                errors=[r["errors"] for r in results_list if r["errors"]]
            )
    except Exception as e:
        logger.error(f"Sync data failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync data: {str(e)}"
        )
@router.post("/generate-report", response_model=GenerateReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_api_key)
):
    """Generate a health report for a user."""
    try:
        result = await _generate_user_report(
            user_id=request.user_id,
            report_type=request.report_type,
            db=db
        )
        
        return GenerateReportResponse(
            success=result["success"],
            user_id=result["user_id"],
            report_type=result["report_type"],
            report_date=result["report_date"],
            content=result["content"],
            errors=result["errors"]
        )
    except Exception as e:
        logger.error(f"Generate report failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )
@router.post("/send-email", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_agent_api_key)
):
    """Send email notification for a user."""
    try:
        result = await _send_user_email(
            user_id=request.user_id,
            report_type=request.report_type,
            custom_content=request.custom_content,
            db=db
        )
        
        return SendEmailResponse(
            success=result["success"],
            user_id=result["user_id"],
            message=result["message"],
            errors=result["errors"]
        )
    except Exception as e:
        logger.error(f"Send email failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )
@router.post("/morning-workflow", response_model=WorkflowResponse)
async def morning_workflow(
    request: WorkflowRequest,
    _: bool = Depends(verify_agent_api_key)
):
    """Execute complete morning workflow."""
    try:
        result = await _execute_morning_workflow(request.user_ids)
        return WorkflowResponse(
            success=result["success"],
            results=result["results"],
            errors=result.get("errors", [])
        )
    except Exception as e:
        logger.error(f"Morning workflow failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute morning workflow: {str(e)}"
        )
@router.post("/evening-workflow", response_model=WorkflowResponse)
async def evening_workflow(
    request: WorkflowRequest,
    _: bool = Depends(verify_agent_api_key)
):
    """Execute complete evening workflow."""
    try:
        result = await _execute_evening_workflow(request.user_ids)
        return WorkflowResponse(
            success=result["success"],
            results=result["results"],
            errors=result.get("errors", [])
        )
    except Exception as e:
        logger.error(f"Evening workflow failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute evening workflow: {str(e)}"
        )
