import logging
from fastapi import status
from sqlalchemy.orm import Session

from app.models.feedback import Feedback, FeedbackStatus
from app.models.user import User
from app.schemas.feedback import FeedbackCreateRequest
from app.tasks import (
    send_feedback_notification_task,
    create_feedback_activity_log_task,
    update_feedback_analytics_cache_task
)

logger = logging.getLogger(__name__)


class FeedbackService:

    @staticmethod
    def submit_feedback(
        db: Session,
        user_id: int,
        payload: FeedbackCreateRequest
    ) -> Feedback:
        """
        Create feedback in database and trigger async background tasks for admin notifications,
        activity logs, and cache updates.
        """
        # Create Feedback instance
        feedback = Feedback(
            user_id=user_id,
            rating=payload.rating,
            category=payload.category,
            message=payload.message,
            status=FeedbackStatus.PENDING,
            device_info=payload.device_info,
            app_version=payload.app_version,
            platform=payload.platform
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        # Trigger Celery/Background workers
        try:
            # 1. Store in DB (done above)
            # 2. Create notification for admins (sends WebSocket to admin panel)
            send_feedback_notification_task(str(feedback.id))
            
            # 3. Log feedback event & Audit log
            user = db.query(User).filter(User.id == user_id).first()
            username = user.username if user else f"User_{user_id}"
            details = f"Feedback ID {feedback.id} submitted: Category={payload.category.value}, Rating={payload.rating}*"
            create_feedback_activity_log_task(str(feedback.id), "FEEDBACK_SUBMITTED", details)
            
            # 4. Increment pending feedback count / update analytics cache
            update_feedback_analytics_cache_task()
        except Exception as e:
            logger.error(f"Failed to dispatch background tasks for feedback {feedback.id}: {str(e)}")

        return feedback
