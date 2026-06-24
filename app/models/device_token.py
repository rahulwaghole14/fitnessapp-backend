from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_token = Column(String(255), unique=True, nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # 'android', 'ios', 'web'
    device_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    failure_count = Column(Integer, default=0, nullable=False)
    last_push_success = Column(DateTime(timezone=True), nullable=True)
    last_push_failure = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship with User
    user = relationship("User", back_populates="device_tokens")

    __table_args__ = (
        Index('idx_device_tokens_user_active', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f"<DeviceToken(id={self.id}, user_id={self.user_id}, platform={self.platform}, is_active={self.is_active})>"
