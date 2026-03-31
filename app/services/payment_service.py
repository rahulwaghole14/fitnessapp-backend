from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional, List
import os
from app.models.payment import Payment, PaymentHistory
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan
from app.schemas.payment import PaymentCreate, PaymentHistoryBase


class PaymentService:
    def __init__(self, db: Session):
        self.db = db

    def create_payment(self, payment_data: PaymentCreate) -> Payment:
        """Create a new payment record"""
        payment = Payment(**payment_data.dict())
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update_payment_status(self, payment_id: int, status: str, transaction_id: Optional[str] = None) -> Optional[
        Payment]:
        """Update payment status"""
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = status
            if transaction_id:
                payment.transaction_id = transaction_id
            self.db.commit()
            self.db.refresh(payment)

            # If payment is completed, create payment history record
            if status == "completed":
                self._create_payment_history(payment)

        return payment

    def get_payments_by_subscription(self, subscription_id: int) -> List[PaymentHistory]:
        """Get all payments for a subscription"""
        # Use PaymentHistory model which has subscription_id field
        return self.db.query(PaymentHistory).filter(PaymentHistory.subscription_id == subscription_id).all()

    def get_payment_history_by_user(self, user_id: int) -> List[PaymentHistory]:
        """Get payment history for a user"""
        return self.db.query(PaymentHistory).filter(PaymentHistory.user_id == user_id).all()

    def get_payments_by_user(self, user_id: int) -> List[Payment]:
        """Get all payments for a user"""
        return self.db.query(Payment).filter(Payment.user_id == user_id).all()

    def get_payment_by_order_id(self, order_id: str) -> Optional[Payment]:
        """Get payment by Razorpay order ID"""
        return self.db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()

    def _create_payment_history(self, payment: Payment):
        """Create payment history record from completed payment"""
        try:
            # Find the subscription linked to this payment
            subscription = self.db.query(Subscription).filter(Subscription.payment_id == payment.id).first()
            if subscription:
                history_data = PaymentHistoryBase(
                    user_id=payment.user_id,
                    subscription_id=subscription.id,
                    plan_id=payment.plan_id,
                    amount=float(payment.amount),
                    status=payment.status,
                    payment_method=payment.payment_method
                )

                payment_history = PaymentHistory(**history_data.dict())
                self.db.add(payment_history)
                self.db.commit()
        except Exception as e:
            # Don't fail the main transaction if history creation fails
            print(f"Failed to create payment history: {str(e)}")

    def process_payment(self, subscription_id: int, amount: float, payment_method: str) -> Payment:
        """Process payment for subscription (legacy method - use Razorpay flow instead)"""
        # This method is deprecated - use the new Razorpay flow
        raise NotImplementedError("Use the new Razorpay flow with /payments/subscribe endpoint")
