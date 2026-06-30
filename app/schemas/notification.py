from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date


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
    scheduled_for: Optional[datetime] = None
    scheduled_time: Optional[str] = None
    scheduled_date: Optional[str] = None

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


class DeviceTokenRegister(BaseModel):
    device_token: str
    platform: str
    device_name: Optional[str] = None


class DeviceTokenUnregister(BaseModel):
    device_token: str


class DeviceTokenResponse(BaseModel):
    id: int
    user_id: int
    device_token: str
    platform: str
    device_name: Optional[str] = None
    is_active: bool
    last_seen: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationPreferenceResponse(BaseModel):
    id: int
    user_id: int
    push_notifications: bool
    meal_reminders: bool
    hydration_reminders: bool
    sleep_notifications: bool
    subscription_notifications: bool
    engagement_notifications: bool

    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    push_notifications: Optional[bool] = None
    meal_reminders: Optional[bool] = None
    hydration_reminders: Optional[bool] = None
    sleep_notifications: Optional[bool] = None
    subscription_notifications: Optional[bool] = None
    engagement_notifications: Optional[bool] = None

