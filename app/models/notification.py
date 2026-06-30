from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=True, index=True)
    priority = Column(String(20), default="normal", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    notification_metadata = Column("metadata", JSON, nullable=True)
    logical_event_id = Column(String(255), unique=True, nullable=True, index=True)
    source_module = Column(String(100), nullable=True)
    delivery_status = Column(String(50), default="PENDING", nullable=True)
    push_sent = Column(Boolean, default=False, nullable=False)
    push_sent_at = Column(DateTime(timezone=True), nullable=True)
    websocket_sent = Column(Boolean, default=False, nullable=False)
    websocket_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship with User
    user = relationship("User")

    @property
    def scheduled_for(self):
        if self.notification_metadata and isinstance(self.notification_metadata, dict):
            # Resolve user's timezone name
            import pytz
            tz_name = self.user.timezone if (self.user and self.user.timezone) else "Asia/Kolkata"
            user_tz = pytz.timezone(tz_name)

            # 1. If scheduled_for is directly stored in metadata, parse and localize to user tz
            val = self.notification_metadata.get("scheduled_for")
            if val:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(val)
                    if dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    return dt.astimezone(user_tz)
                except Exception:
                    pass

            # 2. Reconstruct for Hydration Reminders using slot and date (keep in local user tz)
            if self.notification_type == "HYDRATION_REMINDER":
                date_str = self.notification_metadata.get("date")
                slot_str = self.notification_metadata.get("slot")
                if date_str and slot_str:
                    try:
                        from datetime import datetime, date, time
                        y, m, d = map(int, date_str.split("-"))
                        h, min_val = map(int, slot_str.split(":"))
                        local_dt = datetime.combine(date(y, m, d), time(h, min_val))
                        return user_tz.localize(local_dt)
                    except Exception:
                        pass

            # 3. Reconstruct for Meal Reminders using meal_date or date and template hours (keep in local user tz)
            if self.notification_type and self.notification_type.startswith("MEAL_REMINDER_"):
                meal_date_str = self.notification_metadata.get("meal_date") or self.notification_metadata.get("date")
                if meal_date_str:
                    try:
                        from datetime import datetime, date, time
                        h, min_val = 8, 0
                        if "LUNCH" in self.notification_type:
                            h, min_val = 13, 0
                        elif "DINNER" in self.notification_type:
                            h, min_val = 20, 0
                        y, m, d = map(int, meal_date_str.split("-"))
                        local_dt = datetime.combine(date(y, m, d), time(h, min_val))
                        return user_tz.localize(local_dt)
                    except Exception:
                        pass

            # 4. Reconstruct for Subscription Expiring Alerts using end_date and days_left (keep in local user tz)
            if self.notification_type in ("SUBSCRIPTION_EXPIRING", "SUBSCRIPTION_EXPIRED"):
                end_date_str = self.notification_metadata.get("end_date")
                days_left = self.notification_metadata.get("days_left")
                if end_date_str:
                    try:
                        from datetime import datetime, date, time, timedelta
                        y, m, d = map(int, end_date_str.split("-"))
                        expiry_date = date(y, m, d)
                        days_offset = int(days_left) if days_left is not None else 0
                        target_date = expiry_date - timedelta(days=days_offset)
                        local_dt = datetime.combine(target_date, time(9, 0))
                        return user_tz.localize(local_dt)
                    except Exception:
                        pass
        return None

    @property
    def scheduled_time(self):
        dt = self.scheduled_for
        if dt and hasattr(dt, "strftime"):
            return dt.strftime("%I:%M %p")
        return None

    @property
    def scheduled_date(self):
        dt = self.scheduled_for
        if dt and hasattr(dt, "strftime"):
            return dt.strftime("%Y-%m-%d")
        return None

    # Add indexes for performance optimization
    __table_args__ = (
        Index('idx_notifications_user_read_created', 'user_id', 'is_read', 'created_at'),
        Index('idx_notifications_user_deleted_created', 'user_id', 'is_deleted', 'created_at'),
    )

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, title={self.title}, is_read={self.is_read})>"
