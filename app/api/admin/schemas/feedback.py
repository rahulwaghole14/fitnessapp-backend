"""
Feedback related schemas for admin API
"""
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.models.feedback import FeedbackCategory, FeedbackStatus
from app.schemas.feedback import sanitize_text


class FeedbackResponse(BaseModel):
    id: UUID
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    rating: int
    category: FeedbackCategory
    message: str
    status: FeedbackStatus
    admin_notes: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    app_version: Optional[str] = None
    platform: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackStatusUpdate(BaseModel):
    status: FeedbackStatus = Field(..., description="Feedback status (PENDING, REVIEWED, RESOLVED)")
    admin_notes: Optional[str] = Field(None, description="Optional internal administrative notes")

    @field_validator("admin_notes")
    @classmethod
    def sanitize_admin_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return sanitize_text(v)


class FeedbackAnalyticsSummary(BaseModel):
    total_feedbacks: int
    average_rating: float
    category_distribution: Dict[str, int]
    rating_distribution: Dict[str, int]
    pending_count: int
    resolved_count: int
