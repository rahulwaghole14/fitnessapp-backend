from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: Optional[str] = None
    priority: str
    is_read: bool
    is_deleted: bool
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="notification_metadata", serialization_alias="metadata")
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationMarkReadResponse(BaseModel):
    message: str
    notification_id: int
    is_read: bool


class NotificationSuccessResponse(BaseModel):
    message: str
    success: bool
