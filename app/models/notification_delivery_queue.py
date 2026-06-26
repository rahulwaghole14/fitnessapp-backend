from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class NotificationDeliveryQueue(Base):
    __tablename__ = "notification_delivery_queue"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)  # WEBSOCKET, PUSH
    status = Column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, PROCESSING, SENT, FAILED, RETRY
    priority = Column(String(20), default="NORMAL", nullable=False, index=True)  # HIGH, NORMAL, LOW
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    delivery_started_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        # Optimized index for priority polling including channel
        Index('idx_delivery_queue_channel_status_priority_created', 'channel', 'status', 'priority', 'created_at'),
    )

    def __repr__(self):
        return (f"<NotificationDeliveryQueue(id={self.id}, notification_id={self.notification_id}, "
                f"channel={self.channel}, status={self.status}, priority={self.priority})>")
