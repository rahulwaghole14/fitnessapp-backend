from uuid import UUID
from typing import Optional
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import verify_admin_user
from app.models.admin import Admin
from app.models.feedback import Feedback, FeedbackCategory, FeedbackStatus
from .schemas import (
    FeedbackResponse,
    FeedbackStatusUpdate,
    FeedbackAnalyticsSummary
)
from app.services.feedback_admin_service import FeedbackAdminService
from app.services.feedback_admin_selector import FeedbackAdminSelector


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
# ADMIN HANDLERS
# ==========================================

def list_feedbacks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[FeedbackCategory] = Query(None),
    rating: Optional[int] = Query(None, ge=1, le=5),
    status: Optional[FeedbackStatus] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _ = Depends(verify_admin_user)
):
    """
    Get paginated, filtered list of all feedbacks. (Admin only)
    Ordered by latest.
    """
    list_data = FeedbackAdminSelector.get_admin_feedback_list(
        db=db,
        page=page,
        limit=limit,
        category=category,
        rating=rating,
        status=status,
        search_query=search
    )
    
    mapped_feedbacks = [map_feedback_to_response(f) for f in list_data["feedbacks"]]
    
    return {
        "success": True,
        "total": list_data["total"],
        "page": list_data["page"],
        "limit": list_data["limit"],
        "feedbacks": mapped_feedbacks
    }


def update_feedback_status(
    feedbackId: UUID,
    payload: FeedbackStatusUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(verify_admin_user)
):
    """
    Update the status of a feedback submission and add admin comments. (Admin only)
    """
    feedback = FeedbackAdminService.update_feedback_status(
        db=db,
        feedback_id=feedbackId,
        new_status=payload.status,
        admin_notes=payload.admin_notes,
        admin_id=admin.id
    )
    return map_feedback_to_response(feedback)


def get_feedback_analytics(
    db: Session = Depends(get_db),
    _ = Depends(verify_admin_user)
):
    """
    Get feedback analytics dashboard metrics. (Admin only)
    Uses response caching.
    """
    metrics = FeedbackAdminSelector.get_analytics_cached(db)
    return metrics
