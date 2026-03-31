import razorpay
import os
import hmac
import hashlib
import logging
from typing import Dict, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan

logger = logging.getLogger(__name__)


class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
        )
        self.webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    def create_order(self, amount: float, plan_id: int, user_id: int) -> Dict:
        """Create Razorpay order"""
        try:
            # Convert amount to paise (Razorpay uses paise)
            amount_paise = int(amount * 100)

            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"receipt_{plan_id}_{user_id}_{date.today()}",
                "notes": {
                    "plan_id": str(plan_id),
                    "user_id": str(user_id)
                }
            }

            order = self.client.order.create(data=order_data)
            logger.info(f"Created Razorpay order: {order['id']}")
            return order

        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {str(e)}")
            raise Exception(f"Order creation failed: {str(e)}")

    def verify_webhook_signature(self, razorpay_signature: str, webhook_body: str) -> bool:
        """Verify Razorpay webhook signature"""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                webhook_body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, razorpay_signature)

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False

    def process_payment_webhook(self, webhook_data: Dict, db: Session) -> bool:
        """Process payment webhook and create subscription"""
        try:
            payment_id = webhook_data.get('payload', {}).get('payment', {}).get('entity', {}).get('id')
            order_id = webhook_data.get('payload', {}).get('payment', {}).get('entity', {}).get('order_id')
            status = webhook_data.get('payload', {}).get('payment', {}).get('entity', {}).get('status')

            if not payment_id or not order_id:
                logger.error("Missing payment_id or order_id in webhook")
                return False

            # Lock the payment row for transaction safety
            payment = db.query(Payment).filter(
                Payment.razorpay_order_id == order_id
            ).with_for_update().first()

            if not payment:
                logger.error(f"Payment not found for order_id: {order_id}")
                return False

            # Check if webhook already processed (idempotency)
            if payment.webhook_processed:
                logger.info(f"Webhook already processed for payment: {payment.id}")
                return True

            # Update payment status
            if status == 'captured':
                payment.status = 'completed'
                payment.transaction_id = payment_id
                payment.webhook_processed = True

                # Create subscription
                self._create_subscription_from_payment(payment, db)

                logger.info(f"Payment completed and subscription created: {payment.id}")
                return True
            else:
                payment.status = 'failed'
                payment.webhook_processed = True
                logger.error(f"Payment failed: {payment_id}")
                return False

        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            db.rollback()
            return False

    def _create_subscription_from_payment(self, payment: Payment, db: Session):
        """Create subscription from successful payment"""
        try:
            # Get plan details
            plan = db.query(Plan).filter(Plan.id == payment.plan_id).first()
            if not plan:
                raise Exception(f"Plan not found: {payment.plan_id}")

            # Calculate expiry date
            start_date = date.today()
            end_date = start_date + timedelta(days=plan.duration_days)

            # Check for existing active subscription
            existing_subscription = db.query(Subscription).filter(
                Subscription.user_id == payment.user_id,
                Subscription.status == 'active'
            ).first()

            if existing_subscription:
                # Extend existing subscription
                existing_subscription.end_date = max(existing_subscription.end_date, end_date)
                logger.info(f"Extended existing subscription: {existing_subscription.id}")
            else:
                # Create new subscription
                subscription = Subscription(
                    user_id=payment.user_id,
                    plan_id=payment.plan_id,
                    payment_id=payment.id,
                    start_date=start_date,
                    end_date=end_date,
                    status='active'
                )
                db.add(subscription)
                logger.info(f"Created new subscription: {subscription.id}")

        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise

    def get_payment_status(self, payment_id: str) -> Optional[Dict]:
        """Get payment status from Razorpay"""
        try:
            payment = self.client.payment.fetch(payment_id)
            return payment
        except Exception as e:
            logger.error(f"Failed to fetch payment status: {str(e)}")
            return None
