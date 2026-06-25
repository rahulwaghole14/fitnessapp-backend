from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class PushDeliveryLog(Base):
    __tablename__ = "push_delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_token_id = Column(Integer, ForeignKey("device_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    push_provider = Column(String(50), default="FCM", nullable=False)
    push_message_id = Column(String(255), nullable=True, unique=True, index=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, SENT, FAILED, DELIVERED, OPENED
    error_message = Column(Text, nullable=True)
    notification_type = Column(String(50), nullable=True, index=True)  # Optimized for analytics
    platform = Column(String(50), nullable=True, index=True)  # Optimized for analytics
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_push_logs_user_status', 'user_id', 'status'),
        Index('idx_push_logs_type_status', 'notification_type', 'status'),
        Index('idx_push_logs_platform_status', 'platform', 'status'),
    )

    def __repr__(self):
        return f"<PushDeliveryLog(id={self.id}, notification_id={self.notification_id}, status={self.status})>"
