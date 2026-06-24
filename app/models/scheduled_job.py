from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ScheduledNotificationJob(Base):
    __tablename__ = "scheduled_notification_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(String, nullable=False)
    notification_metadata = Column("metadata", JSON, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    job_key = Column(String(255), unique=True, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship with User
    user = relationship("User")

    __table_args__ = (
        Index('idx_jobs_status_scheduled', 'status', 'scheduled_for'),
        Index('idx_jobs_user_scheduled', 'user_id', 'scheduled_for'),
    )

    def __repr__(self):
        return f"<ScheduledNotificationJob(id={self.id}, user_id={self.user_id}, type={self.notification_type}, status={self.status})>"
