"""
Verification Script for Advanced User Notification System
"""
import sys
import os
import uuid
import asyncio
from datetime import datetime, date, time, timedelta
import pytz

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.notification import Notification
from app.models.activity import DailyActivity
from app.models.sleep import SleepSession, UserDailySleep, UserMonthlySleep, UserYearlySleep
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan
from app.models.payment import Payment
from app.models.user_activity_log import UserActivityLog
from app.models.refresh_token import RefreshToken
from app.services.notification_service import notification_service
from app.services.scheduler import (
    meal_reminder_job,
    hydration_reminder_job,
    subscription_expiry_job,
    inactivity_reminder_job
)
from app.services.sleep_service import SleepService
from app.schemas.sleep import SleepSessionCreate


def safe_str(s: str) -> str:
    """Safe ASCII representation of a string for cp1252 Windows console."""
    if s is None:
        return ""
    return s.encode('ascii', 'replace').decode('ascii')


def run_tests():
    print("====================================================")
    print("STARTING ADVANCED USER NOTIFICATION SYSTEM VERIFICATION")
    print("====================================================")
    
    db = SessionLocal()
    test_user_email = "notif_tester_999@example.com"
    test_user = None
    
    try:
        # 0. Cleanup any stale test user
        stale = db.query(User).filter(User.email == test_user_email).first()
        if stale:
            print("Cleaning up stale test user from previous run...")
            db.query(Notification).filter(Notification.user_id == stale.id).delete()
            db.query(Subscription).filter(Subscription.user_id == stale.id).delete()
            db.query(SleepSession).filter(SleepSession.user_id == stale.id).delete()
            db.query(UserDailySleep).filter(UserDailySleep.user_id == stale.id).delete()
            db.query(UserMonthlySleep).filter(UserMonthlySleep.user_id == stale.id).delete()
            db.query(UserYearlySleep).filter(UserYearlySleep.user_id == stale.id).delete()
            db.query(DailyActivity).filter(DailyActivity.user_id == stale.id).delete()
            db.query(UserActivityLog).filter(UserActivityLog.user_id == stale.id).delete()
            db.delete(stale)
            db.commit()
            
        # Create fresh test user
        test_user = User(
            username="notif_tester_999",
            email=test_user_email,
            password="testpassword",
            timezone="Asia/Kolkata",
            sleep_goal=480  # 8 hours
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        user_id = test_user.id
        print(f"Success: Created test user with ID: {user_id}")

        # ----------------------------------------------------
        # 1. TEST MEAL REMINDERS
        # ----------------------------------------------------
        print("\n--- Testing Meal Reminders ---")
        asyncio.run(meal_reminder_job())
        
        # Check database
        db.expire_all()
        meal_notifs = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type.in_(["MEAL_REMINDER_BREAKFAST", "MEAL_REMINDER_LUNCH", "MEAL_REMINDER_DINNER"])
        ).all()
        print(f"Triggered meal reminder job. Created {len(meal_notifs)} notification(s).")
        for n in meal_notifs:
            print(f"  - {safe_str(n.notification_type)}: {safe_str(n.title)} - '{safe_str(n.message)}'")
            assert "Breakfast" in n.title or "Lunch" in n.title or "Dinner" in n.title
            assert n.priority == "normal"
            
        # ----------------------------------------------------
        # 2. TEST HYDRATION REMINDERS
        # ----------------------------------------------------
        print("\n--- Testing Hydration Reminders ---")
        asyncio.run(hydration_reminder_job())
        db.expire_all()
        hydration_notifs = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "HYDRATION_REMINDER"
        ).all()
        print(f"Triggered hydration reminder job. Created {len(hydration_notifs)} notification(s).")
        for n in hydration_notifs:
            print(f"  - {safe_str(n.notification_type)} slot {safe_str(n.notification_metadata.get('slot'))}: {safe_str(n.title)} - '{safe_str(n.message)}'")
            assert "Hydration" in n.title
            assert n.priority == "normal"

        # ----------------------------------------------------
        # 3. TEST SUBSCRIPTION EXPIRATION REMINDERS
        # ----------------------------------------------------
        print("\n--- Testing Subscription Expiration Reminders ---")
        # Let's create subscription plans if none exist
        plan = db.query(Plan).first()
        if not plan:
            plan = Plan(name="Premium Test", description="Test Plan", price=199.00, duration_days=30, features="All")
            db.add(plan)
            db.commit()
            db.refresh(plan)
            
        payment = db.query(Payment).first()
        if not payment:
            payment = Payment(user_id=user_id, plan_id=plan.id, amount=199.00, status="completed", razorpay_order_id="order_123")
            db.add(payment)
            db.commit()
            db.refresh(payment)

        # A. Test 7 days before
        sub_7_days = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            payment_id=payment.id,
            start_date=date.today() - timedelta(days=23),
            end_date=date.today() + timedelta(days=7),
            status="active"
        )
        db.add(sub_7_days)
        db.commit()
        
        asyncio.run(subscription_expiry_job())
        db.expire_all()
        exp_7_notifs = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "SUBSCRIPTION_EXPIRING"
        ).all()
        assert len(exp_7_notifs) >= 1
        print("Success: Verified 7-day Subscription Expiring Notification created successfully.")
        print(f"  Payload: {safe_str(exp_7_notifs[0].title)} - '{safe_str(exp_7_notifs[0].message)}' [Priority: {exp_7_notifs[0].priority}]")
        assert exp_7_notifs[0].priority == "high"
        
        # Clean up this subscription
        db.delete(sub_7_days)
        db.commit()

        # B. Test 1 day before
        sub_1_day = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            payment_id=payment.id,
            start_date=date.today() - timedelta(days=29),
            end_date=date.today() + timedelta(days=1),
            status="active"
        )
        db.add(sub_1_day)
        db.commit()
        
        asyncio.run(subscription_expiry_job())
        db.expire_all()
        exp_1_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "SUBSCRIPTION_EXPIRING"
        ).all()
        assert len(exp_1_notif) >= 2  # one from 7-day, one from 1-day
        print("Success: Verified 1-day Subscription Expiring Notification created successfully.")
        assert any(n.notification_metadata.get("days_left") == 1 for n in exp_1_notif)
        
        # Clean up this subscription
        db.delete(sub_1_day)
        db.commit()

        # C. Test expired subscription
        sub_expired = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            payment_id=payment.id,
            start_date=date.today() - timedelta(days=35),
            end_date=date.today() - timedelta(days=1),
            status="active"
        )
        db.add(sub_expired)
        db.commit()
        
        asyncio.run(subscription_expiry_job())
        db.expire_all()
        expired_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "SUBSCRIPTION_EXPIRED"
        ).first()
        assert expired_notif is not None
        print("Success: Verified Subscription Expired Notification created successfully.")
        print(f"  Payload: {safe_str(expired_notif.title)} - '{safe_str(expired_notif.message)}' [Priority: {expired_notif.priority}]")
        assert expired_notif.priority == "high"
        
        # Verify status is updated to 'expired'
        db.refresh(sub_expired)
        assert sub_expired.status == "expired"
        print("Success: Verified subscription database status updated to 'expired' successfully.")
        
        db.delete(sub_expired)
        db.commit()

        # ----------------------------------------------------
        # 4. TEST SLEEP ACHIEVEMENT NOTIFICATIONS
        # ----------------------------------------------------
        print("\n--- Testing Sleep Goal Achievement Notifications ---")
        
        # A. Create a sleep session of exactly 8 hours (480 minutes) to get a score of 95 (75 base + 10 + 10)
        sleep_start = datetime.utcnow() - timedelta(hours=8)
        sleep_end = datetime.utcnow()
        
        # Call SleepService.create_sleep_session which triggers achievements automatically
        payload = SleepSessionCreate(
            id=str(uuid.uuid4()),
            startTime=sleep_start,
            endTime=sleep_end,
            isNap=False,
            source="test",
            timezone="Asia/Kolkata",
            deepSleepMinutes=96,   # exactly 20%
            lightSleepMinutes=288, # 60%
            remSleepMinutes=96,    # exactly 20%
            awakeMinutes=0
        )
        
        session = SleepService.create_sleep_session(db, user_id, payload)
        db.expire_all()
        
        print(f"Created Sleep Session. Duration: {session.duration_minutes} mins, Score: {session.sleep_score}")
        
        # Verify notifications in db
        sleep_achieved_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "SLEEP_GOAL_ACHIEVED"
        ).first()
        sleep_excellent_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "SLEEP_ACHIEVEMENT"
        ).first()
        
        assert sleep_achieved_notif is not None
        print(f"Success: Verified SLEEP_GOAL_ACHIEVED triggered. Payload: {safe_str(sleep_achieved_notif.title)} - '{safe_str(sleep_achieved_notif.message)}'")
        
        assert sleep_excellent_notif is not None
        print(f"Success: Verified SLEEP_ACHIEVEMENT triggered. Payload: {safe_str(sleep_excellent_notif.title)} - '{safe_str(sleep_excellent_notif.message)}'")

        # ----------------------------------------------------
        # 5. TEST USER ENGAGEMENT NOTIFICATIONS (WELCOME / PROFILE SETUP)
        # ----------------------------------------------------
        print("\n--- Testing User Engagement Notifications ---")
        # Trigger engagement notifications
        notification_service.trigger_engagement_notifications(db, user_id)
        db.expire_all()
        
        welcome_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "WELCOME"
        ).first()
        profile_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "PROFILE_COMPLETED"
        ).first()
        
        assert welcome_notif is not None
        print(f"Success: Verified WELCOME notification triggered: {safe_str(welcome_notif.title)} - '{safe_str(welcome_notif.message)}'")
        assert profile_notif is not None
        print(f"Success: Verified PROFILE_COMPLETED notification triggered: {safe_str(profile_notif.title)} - '{safe_str(profile_notif.message)}'")

        # ----------------------------------------------------
        # 6. TEST INACTIVITY REMINDERS
        # ----------------------------------------------------
        print("\n--- Testing Inactivity Reminder Notifications ---")
        # A. If we have logged sleep or activities, inactivity job should NOT fire.
        # Let's delete the sleep session we just created so the user has no activities in the last 3 days
        db.query(SleepSession).filter(SleepSession.user_id == user_id).delete()
        db.query(UserDailySleep).filter(UserDailySleep.user_id == user_id).delete()
        db.query(UserMonthlySleep).filter(UserMonthlySleep.user_id == user_id).delete()
        db.query(UserYearlySleep).filter(UserYearlySleep.user_id == user_id).delete()
        db.query(DailyActivity).filter(DailyActivity.user_id == user_id).delete()
        db.query(UserActivityLog).filter(UserActivityLog.user_id == user_id).delete()
        db.commit()
        
        # Now run the inactivity job
        asyncio.run(inactivity_reminder_job())
        db.expire_all()
        
        inactivity_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "INACTIVITY_REMINDER"
        ).first()
        
        assert inactivity_notif is not None
        print(f"Success: Verified INACTIVITY_REMINDER notification triggered. Payload: {safe_str(inactivity_notif.title)} - '{safe_str(inactivity_notif.message)}'")

        # ----------------------------------------------------
        # 7. CLEANUP
        # ----------------------------------------------------
        print("\nCleaning up test user data...")
        db.query(Notification).filter(Notification.user_id == user_id).delete()
        db.query(Subscription).filter(Subscription.user_id == user_id).delete()
        db.query(SleepSession).filter(SleepSession.user_id == user_id).delete()
        db.query(UserDailySleep).filter(UserDailySleep.user_id == user_id).delete()
        db.query(UserMonthlySleep).filter(UserMonthlySleep.user_id == user_id).delete()
        db.query(UserYearlySleep).filter(UserYearlySleep.user_id == user_id).delete()
        db.query(DailyActivity).filter(DailyActivity.user_id == user_id).delete()
        db.query(UserActivityLog).filter(UserActivityLog.user_id == user_id).delete()
        db.delete(test_user)
        db.commit()
        print("Success: Cleanup completed.")
        
        print("\n====================================================")
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("====================================================")
        
    except Exception as e:
        print(f"\nError: Test Failed: {safe_str(str(e))}")
        import traceback
        traceback.print_exc()
        # Ensure cleanup on fail
        if test_user and test_user.id:
            try:
                db.query(Notification).filter(Notification.user_id == test_user.id).delete()
                db.query(Subscription).filter(Subscription.user_id == test_user.id).delete()
                db.query(SleepSession).filter(SleepSession.user_id == test_user.id).delete()
                db.query(UserDailySleep).filter(UserDailySleep.user_id == test_user.id).delete()
                db.query(UserMonthlySleep).filter(UserMonthlySleep.user_id == test_user.id).delete()
                db.query(UserYearlySleep).filter(UserYearlySleep.user_id == test_user.id).delete()
                db.query(DailyActivity).filter(DailyActivity.user_id == test_user.id).delete()
                db.query(UserActivityLog).filter(UserActivityLog.user_id == test_user.id).delete()
                db.delete(test_user)
                db.commit()
            except Exception as clean_err:
                print(f"Failed to clean up: {safe_str(str(clean_err))}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
