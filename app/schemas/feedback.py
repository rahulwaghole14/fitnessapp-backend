import html
import re
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.models.feedback import FeedbackCategory, FeedbackStatus

# Sanitization helper to protect against XSS and SQL injection
def sanitize_text(text: str) -> str:
    if not text:
        return ""
    # Strip HTML tags
    clean_text = re.sub(r"<[^>]*>", "", text)
    # Escape HTML special characters
    return html.escape(clean_text.strip())


class FeedbackCreateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    category: FeedbackCategory = Field(..., description="Feedback category (WORKOUTS, NUTRITION, DESIGN, BUG_REPORT, OTHER)")
    message: str = Field(..., min_length=10, max_length=500, description="Feedback message between 10 and 500 characters")
    device_info: Optional[Dict[str, Any]] = Field(None, description="Optional device details in JSON format")
    app_version: Optional[str] = Field(None, max_length=50, description="Optional mobile app version")
    platform: Optional[str] = Field(None, max_length=50, description="Optional mobile platform (Android/iOS)")

    @field_validator("message")
    @classmethod
    def sanitize_message_text(cls, v: str) -> str:
        sanitized = sanitize_text(v)
        # Ensure message is still valid length after stripping HTML tags
        if len(sanitized) < 10:
            raise ValueError("Message must contain at least 10 non-HTML characters")
        if len(sanitized) > 500:
            raise ValueError("Message must not exceed 500 characters")
        return sanitized


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


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = {}
