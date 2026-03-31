from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth_dependencies import get_current_user
from app.services.razorpay_service import RazorpayService
from app.schemas.payment import PaymentCreate, PaymentHistory, OrderResponse, SubscriptionRequest
from app.services.payment_service import PaymentService
from app.models.payment import Payment as PaymentModel
from app.models.subscription import Subscription

from app.models.subscription_plans import Plan as PlanModel
import json

# Initialize Razorpay service
razorpay_service = RazorpayService()

def get_all_plans(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    plans = db.query(PlanModel).filter(PlanModel.is_active == True).all()
    return plans

def get_plan_id(plan_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    plan = db.query(PlanModel).filter(
    PlanModel.id == plan_id,
    PlanModel.is_active == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def create_subscription_order(request: SubscriptionRequest, db: Session = Depends(get_db),
                              current_user=Depends(get_current_user)):
    """Create Razorpay order for subscription (user only)"""
    try:
        # ✅ Use authenticated user's ID instead of request.user_id
        user_id = current_user.id

        # Check if user already has active subscription
        from app.models.subscription import Subscription
        existing_subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == 'active'
        ).first()

        if existing_subscription:
            raise HTTPException(status_code=400, detail="User already has an active subscription")

        # Get plan details
        plan = db.query(PlanModel).filter(PlanModel.id == request.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Create Razorpay order
        razorpay_service = RazorpayService()
        order = razorpay_service.create_order(float(plan.price), request.plan_id, user_id)  # ✅ Use user_id variable

        # Save payment record
        payment_data = PaymentCreate(
            user_id=user_id,  # ✅ Use user_id variable
            plan_id=request.plan_id,
            amount=float(plan.price),
            payment_method="razorpay",
            razorpay_order_id=order['id']
        )

        payment_service = PaymentService(db)
        payment = payment_service.create_payment(payment_data)

        return OrderResponse(
            order_id=order['id'],
            amount=order['amount'],
            #  currency=order['currency'],
            receipt=order['receipt'],
            notes=order['notes']
        )

    except Exception as e:
        print(f"Failed to create subscription order: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Order creation failed: {str(e)}")


# @router.post("/webhooks/razorpay")
async def handle_razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Razorpay webhook events"""
    try:
        # Get webhook body
        webhook_body = await request.body()
        webhook_data = json.loads(webhook_body.decode('utf-8'))

        # Get signature
        razorpay_signature = request.headers.get('X-Razorpay-Signature')
        if not razorpay_signature:
            raise HTTPException(status_code=400, detail="Missing webhook signature")

        # Verify signature
        if not razorpay_service.verify_webhook_signature(razorpay_signature, webhook_body.decode('utf-8')):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        # Process webhook
        event_type = webhook_data.get('event')
        print(f"Processing webhook event: {event_type}")

        if event_type == 'payment.captured':
            success = razorpay_service.process_payment_webhook(webhook_data, db)
            if success:
                return {"status": "success", "message": "Payment processed successfully"}
            else:
                return {"status": "error", "message": "Payment processing failed"}
        elif event_type == 'payment.failed':
            # Handle failed payment
            payment_id = webhook_data.get('payload', {}).get('payment', {}).get('entity', {}).get('order_id')
            payment = db.query(PaymentModel).filter(
                PaymentModel.razorpay_order_id == payment_id
            ).first()
            if payment:
                payment.status = 'failed'
                payment.webhook_processed = True
                db.commit()
            return {"status": "success", "message": "Payment failure recorded"}
        else:
            print(f"Unhandled webhook event: {event_type}")
            return {"status": "success", "message": "Event received"}

    except Exception as e:
        print(f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Webhook processing failed: {str(e)}")



def get_payment_history(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Use JWT user ID - no user_id parameter needed
    return db.query(PaymentHistory).filter(PaymentHistory.user_id == current_user.id).all()


def get_user_subscription(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get subscription details for authenticated user (from JWT)"""
    # Get user's active subscription from user_subscriptions table
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == 'active'
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    # Return subscription details with plan information
    return {
        "id": subscription.id,
        "user_id": subscription.user_id,
        "plan_id": subscription.plan_id,
        "payment_id": subscription.payment_id,
        "start_date": subscription.start_date,
        "end_date": subscription.end_date,
        "status": subscription.status,
        "auto_renew": subscription.auto_renew,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
        "plan": {
            "id": subscription.plan.id,
            "name": subscription.plan.name,
            "description": subscription.plan.description,
            "price": float(subscription.plan.price),
            "duration_days": subscription.plan.duration_days,
            "features": subscription.plan.features
        } if subscription.plan else None
    }