from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50))  # razorpay, etc.
    status = Column(String(20), default="created")  # created, pending, completed, failed
    transaction_id = Column(String(255))  # Razorpay payment ID
    razorpay_order_id = Column(String(100))  # Razorpay order ID
    webhook_processed = Column(Boolean, default=False)  # Track webhook processing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    plan = relationship("Plan", backref="payments")

class PaymentHistory(Base):
    __tablename__ = "payment_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), nullable=False)
    payment_method = Column(String(50))

    # Relationships
    subscription = relationship("Subscription", backref="payment_history")
    plan = relationship("Plan", backref="payment_history")
