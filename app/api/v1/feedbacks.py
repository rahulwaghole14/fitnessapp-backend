from uuid import UUID
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user_id
from app.core.throttles import feedback_rate_limiter
from app.core.permissions import verify_feedback_ownership
from app.models.feedback import Feedback, FeedbackStatus
from app.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackResponse,
    StandardResponse
)
from app.services.feedback_service import FeedbackService
from app.services.feedback_selector import FeedbackSelector


# Helper to map a Feedback SQLAlchemy model to response dict (pre-loads User metadata)
def map_feedback_to_response(feedback: Feedback) -> dict:
    return {
        "id": feedback.id,
        "user_id": feedback.user_id,
        "username": feedback.user.username if feedback.user else None,
        "email": feedback.user.email if feedback.user else None,
        "rating": feedback.rating,
        "category": feedback.category,
        "message": feedback.message,
        "status": feedback.status,
        "admin_notes": feedback.admin_notes,
        "device_info": feedback.device_info,
        "app_version": feedback.app_version,
        "platform": feedback.platform,
        "created_at": feedback.created_at,
        "updated_at": feedback.updated_at
    }


# ==========================================
# USER HANDLERS
# ==========================================

def submit_feedback(
    payload: FeedbackCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    _ = Depends(feedback_rate_limiter)
):
    """
    Submit app feedback from the mobile application.
    Enforces a rate limit of 5 submissions per user per hour.
    """
    feedback = FeedbackService.submit_feedback(
        db=db,
        user_id=user_id,
        payload=payload
    )
    
    return StandardResponse(
        success=True,
        message="Feedback submitted successfully",
        data={"feedback_id": str(feedback.id)}
    )


def get_my_feedback_history(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get all feedback submitted by the authenticated user.
    """
    feedbacks = FeedbackSelector.get_user_feedback_history(db=db, user_id=user_id)
    return [map_feedback_to_response(f) for f in feedbacks]


def get_feedback_details(
    feedbackId: UUID,
    db: Session = Depends(get_db),
    feedback: Feedback = Depends(verify_feedback_ownership)
):
    """
    Get detailed information about a feedback submission.
    Users can only access their own feedbacks.
    """
    return map_feedback_to_response(feedback)

