from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    push_notifications = Column(Boolean, default=True, nullable=False)
    meal_reminders = Column(Boolean, default=True, nullable=False)
    hydration_reminders = Column(Boolean, default=True, nullable=False)
    sleep_notifications = Column(Boolean, default=True, nullable=False)
    subscription_notifications = Column(Boolean, default=True, nullable=False)
    engagement_notifications = Column(Boolean, default=True, nullable=False)

    # Relationship with User
    user = relationship("User", back_populates="notification_preference")

    def __repr__(self):
        return (f"<NotificationPreference(id={self.id}, user_id={self.user_id}, "
                f"push_notifications={self.push_notifications})>")
