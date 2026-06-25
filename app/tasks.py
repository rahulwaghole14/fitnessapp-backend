import logging
import os
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.feedback import Feedback
from app.models.user import User
from app.utils.activity_logger import log_activity

logger = logging.getLogger(__name__)


# Thread-safe global analytics cache
# Allows storing pre-computed metrics to respond instantly to admin dashboards
ANALYTICS_CACHE = {
    "analytics": None
}


def send_feedback_notification_task(feedback_id: str):
    """
    Synchronous task to notify admins via WebSocket when a new feedback is submitted.
    Creates an activity log with category 'FEEDBACK_SUBMITTED' and broadcasts it.
    """
    db: Session = SessionLocal()
    try:
        from uuid import UUID
        feedback_uuid = UUID(feedback_id)
        feedback = db.query(Feedback).filter(
            Feedback.id == feedback_uuid
        ).first()
        
        if not feedback:
            logger.error(f"Feedback {feedback_id} not found for notification task.")
            return

        user = db.query(User).filter(User.id == feedback.user_id).first()
        username = user.username if user else f"User_{feedback.user_id}"

        # Formulate description for activity log
        description = f"New feedback submitted by {username} - Category: {feedback.category.value if hasattr(feedback.category, 'value') else feedback.category}, Rating: {feedback.rating}*, Status: {feedback.status.value if hasattr(feedback.status, 'value') else feedback.status}"
        
        # log_activity automatically sends Websocket message if send_notification=True
        log_activity(db, feedback.user_id, username, "feedback_submitted", description, send_notification=True)
        logger.info(f"Feedback submission notification sent for Feedback ID: {feedback_id}")
    except Exception as e:
        logger.error(f"Error in send_feedback_notification_task: {str(e)}")
    finally:
        db.close()


def create_feedback_activity_log_task(feedback_id: str, action: str, details: str):
    """
    Synchronous task to create audit activity logs for feedback operations:
    Created, Status Changed, Admin Notes Added, etc.
    """
    db: Session = SessionLocal()
    try:
        from uuid import UUID
        feedback_uuid = UUID(feedback_id)
        feedback = db.query(Feedback).filter(Feedback.id == feedback_uuid).first()
        if not feedback:
            logger.error(f"Feedback {feedback_id} not found for activity logging.")
            return

        user = db.query(User).filter(User.id == feedback.user_id).first()
        username = user.username if user else "System"

        # Log audit trail activity
        log_activity(
            db=db,
            user_id=feedback.user_id,
            username=username,
            activity_type=action,
            description=details,
            send_notification=False
        )
        logger.info(f"Audit log recorded: {action} - {details}")
    except Exception as e:
        logger.error(f"Error in create_feedback_activity_log_task: {str(e)}")
    finally:
        db.close()


def update_feedback_analytics_cache_task():
    """
    Synchronous task to recalculate feedback analytics and update the in-memory cache.
    """
    db: Session = SessionLocal()
    try:
        from app.services.feedback_admin_selector import FeedbackAdminSelector
        logger.info("Recalculating feedback analytics cache...")

        analytics = FeedbackAdminSelector.compute_analytics(db)
        
        # Save to local cache
        ANALYTICS_CACHE["analytics"] = analytics

        logger.info("Feedback analytics cache successfully updated.")
    except Exception as e:
        logger.error(f"Error in update_feedback_analytics_cache_task: {str(e)}")
    finally:
        db.close()
