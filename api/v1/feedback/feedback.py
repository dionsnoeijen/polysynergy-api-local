from fastapi import APIRouter, Depends, BackgroundTasks
from models import Account
from schemas.feedback import FeedbackCreate, FeedbackResponse
from services.email.email_service import EmailService
from utils.get_current_account import get_current_account
from core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    background_tasks: BackgroundTasks,
    account: Account = Depends(get_current_account),
):
    """
    Submit user feedback that will be emailed to the admin.
    Requires authentication.
    """
    try:
        # Format timestamp for email
        timestamp_str = feedback.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Send feedback email in background
        EmailService.send_feedback_email(
            user_email=feedback.email,
            message=feedback.message,
            timestamp=timestamp_str,
            user_agent=feedback.user_agent,
            background_tasks=background_tasks
        )

        logger.info(
            f"Feedback submitted by {account.email} ({account.id})",
            extra={
                "account_id": str(account.id),
                "feedback_email": feedback.email,
                "message_length": len(feedback.message)
            }
        )

        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully"
        )

    except Exception as e:
        logger.error(
            f"Failed to submit feedback: {str(e)}",
            extra={
                "account_id": str(account.id),
                "error": str(e)
            }
        )
        return FeedbackResponse(
            success=False,
            message="Failed to submit feedback"
        )
