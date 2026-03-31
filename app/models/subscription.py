from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Subscription(Base):
    __tablename__ = "user_subscriptions"  # Changed from "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)  # Link to payment
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="active")  # active, expired, cancelled
    auto_renew = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    plan = relationship("Plan", backref="user_subscriptions")
    payment = relationship("Payment", backref="user_subscriptions")

    # Add constraint to prevent duplicate active subscriptions
    __table_args__ = (UniqueConstraint('user_id', 'status', name='unique_active_subscription'),)
