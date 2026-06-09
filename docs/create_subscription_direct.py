from app.core.database import get_db
from app.models.user import User
from app.models.subscription_plans import Plan
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.refresh_token import RefreshToken
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

def create_subscription_directly():
    """Create subscription directly in database for user Jagga Daku"""
    
    # Create a database session
    db = next(get_db())
    
    try:
        # Step 1: Find the user
        user = db.query(User).filter(User.email == 'jd@gmail.com').first()
        if not user:
            print("User 'Jagga Daku' with email 'jd@gmail.com' not found")
            return
        
        print(f"Found user: ID={user.id}, Username={user.username}, Email={user.email}")
        
        # Step 2: Check if user already has active subscription
        existing_subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == 'active'
        ).first()
        
        if existing_subscription:
            print(f"User already has an active subscription: ID={existing_subscription.id}")
            print("Subscription details:")
            print(f"  Plan ID: {existing_subscription.plan_id}")
            print(f"  Start Date: {existing_subscription.start_date}")
            print(f"  End Date: {existing_subscription.end_date}")
            print(f"  Status: {existing_subscription.status}")
            return
        
        # Step 3: Get available plans
        plans = db.query(Plan).filter(Plan.is_active == True).all()
        print(f"\nAvailable plans:")
        for plan in plans:
            print(f"ID={plan.id}, Name={plan.name}, Price={plan.price}, Duration={plan.duration_days} days")
        
        # Step 4: Use plan ID 4 (test plan)
        plan = db.query(Plan).filter(Plan.id == 4).first()
        if not plan:
            print("Plan ID 4 not found")
            return
        
        print(f"\nUsing plan: {plan.name} (ID={plan.id}, Price={plan.price})")
        
        # Step 5: Create payment record
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            amount=float(plan.price),
            payment_method="razorpay",
            status="completed",
            transaction_id=f"demo_payment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            razorpay_order_id=f"demo_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            webhook_processed=True
        )
        
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        print(f"Created payment record: ID={payment.id}, Status={payment.status}")
        
        # Step 6: Create subscription
        start_date = date.today()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            payment_id=payment.id,
            start_date=start_date,
            end_date=end_date,
            status="active",
            auto_renew=True
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        print(f"\nSubscription created successfully!")
        print(f"Subscription ID: {subscription.id}")
        print(f"User: {user.username} ({user.email})")
        print(f"Plan: {plan.name}")
        print(f"Start Date: {subscription.start_date}")
        print(f"End Date: {subscription.end_date}")
        print(f"Status: {subscription.status}")
        print(f"Payment ID: {payment.id}")
        
        # Step 7: Create payment history record
        from app.models.payment import PaymentHistory
        payment_history = PaymentHistory(
            user_id=user.id,
            subscription_id=subscription.id,
            plan_id=plan.id,
            amount=float(plan.price),
            status="completed",
            payment_method="razorpay",
            payment_date=datetime.utcnow()
        )
        
        db.add(payment_history)
        db.commit()
        
        print(f"Payment history record created: ID={payment_history.id}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_subscription_directly()
