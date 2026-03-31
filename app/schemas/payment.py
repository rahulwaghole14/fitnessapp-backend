from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class PaymentBase(BaseModel):
    user_id: int
    plan_id: int
    amount: float
    payment_method: Optional[str] = "razorpay"


class PaymentCreate(PaymentBase):
    razorpay_order_id: str


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    transaction_id: Optional[str] = None
    webhook_processed: Optional[bool] = None


class Payment(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    transaction_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    webhook_processed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaymentHistoryBase(BaseModel):
    user_id: int
    subscription_id: int
    plan_id: int
    amount: float
    status: str
    payment_method: Optional[str] = None


class PaymentHistory(PaymentHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_date: datetime


class SubscriptionRequest(BaseModel):
    plan_id: int  # ✅ Removed user_id - user should only subscribe for themselves


class OrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    receipt: str
    notes: dict
