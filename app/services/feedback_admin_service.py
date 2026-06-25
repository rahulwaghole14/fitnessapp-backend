import logging
from uuid import UUID
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.feedback import Feedback, FeedbackStatus
from app.tasks import (
    create_feedback_activity_log_task,
    update_feedback_analytics_cache_task
)

logger = logging.getLogger(__name__)


class FeedbackAdminService:

    @staticmethod
    def update_feedback_status(
        db: Session,
        feedback_id: UUID,
        new_status: FeedbackStatus,
        admin_notes: Optional[str],
        admin_id: int
    ) -> Feedback:
        """
        Update feedback status and administrative internal comments.
        Logs activity audit log and triggers cache updates.
        """
        feedback = db.query(Feedback).filter(
            Feedback.id == feedback_id
        ).first()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )

        old_status = feedback.status
        feedback.status = new_status
        if admin_notes is not None:
            feedback.admin_notes = admin_notes
            
        db.commit()
        db.refresh(feedback)

        # Create activity audit log
        details = f"Feedback status changed from {old_status} to {new_status} by Admin ID {admin_id}"
        if admin_notes:
            details += f". Notes added: '{admin_notes}'"
            
        try:
            create_feedback_activity_log_task(str(feedback.id), "FEEDBACK_UPDATED", details)
            update_feedback_analytics_cache_task()
        except Exception as e:
            logger.error(f"Failed to execute background task for status change of feedback {feedback_id}: {str(e)}")

        return feedback
