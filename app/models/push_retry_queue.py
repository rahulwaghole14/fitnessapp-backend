from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class PushRetryQueue(Base):
    __tablename__ = "push_retry_queue"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    device_token_id = Column(Integer, ForeignKey("device_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, PROCESSING, SENT, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_push_retry_status_time', 'status', 'next_retry_at'),
    )

    def __repr__(self):
        return f"<PushRetryQueue(id={self.id}, notification_id={self.notification_id}, retry_count={self.retry_count}, status={self.status})>"
