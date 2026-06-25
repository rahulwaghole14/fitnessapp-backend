import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

class FeedbackCategory(str, enum.Enum):
    WORKOUTS = "WORKOUTS"
    NUTRITION = "NUTRITION"
    DESIGN = "DESIGN"
    BUG_REPORT = "BUG_REPORT"
    OTHER = "OTHER"


class FeedbackStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False, index=True)
    category = Column(SQLEnum(FeedbackCategory, name="feedback_category_enum"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(SQLEnum(FeedbackStatus, name="feedback_status_enum"), default=FeedbackStatus.PENDING, nullable=False, index=True)
    admin_notes = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)
    app_version = Column(String(50), nullable=True)
    platform = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("idx_feedback_user_category", "user_id", "category"),
        Index("idx_feedback_status_created_at", "status", "created_at"),
    )

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, rating={self.rating}, category='{self.category}', status='{self.status}')>"
