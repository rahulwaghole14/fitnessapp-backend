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

    # Add indexes for performance optimization
    __table_args__ = (
        Index('idx_notifications_user_read_created', 'user_id', 'is_read', 'created_at'),
        Index('idx_notifications_user_deleted_created', 'user_id', 'is_deleted', 'created_at'),
    )

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, title={self.title}, is_read={self.is_read})>"
