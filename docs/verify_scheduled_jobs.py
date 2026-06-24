import sys
import os
import asyncio
import uuid
from datetime import datetime, date, time, timedelta, timezone
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.notification import Notification
from app.models.scheduled_job import ScheduledNotificationJob
from app.models.device_token import DeviceToken
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan
from app.models.payment import Payment

from app.services.notification_job_generator import (
    generate_meal_jobs_for_user,
    generate_hydration_jobs_for_user,
    reschedule_inactivity_reminder,
    generate_subscription_expiry_jobs
)
from app.services.notification_worker import process_pending_jobs
from app.services.push_service import push_service

def clean_test_user(db: Session, email: str):
    """Clean up test user data."""
    stale = db.query(User).filter(User.email == email).first()
    if stale:
        print(f"Cleaning up test user {stale.id} data...")
        db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.user_id == stale.id).delete()
        db.query(Notification).filter(Notification.user_id == stale.id).delete()
        db.query(DeviceToken).filter(DeviceToken.user_id == stale.id).delete()
        db.query(Subscription).filter(Subscription.user_id == stale.id).delete()
        db.delete(stale)
        db.commit()

async def test_scheduled_notifications():
    print("====================================================")
    print("STARTING SCHEDULED NOTIFICATION SYSTEM VERIFICATION")
    print("====================================================")
    
    db = SessionLocal()
    test_email = "job_tester_123@example.com"
    
    try:
        clean_test_user(db, test_email)
        
        # 1. Create a test user with Asia/Kolkata timezone (+05:30)
        user = User(
            username="job_tester_123",
            email=test_email,
            password="testpassword",
            timezone="Asia/Kolkata"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
        print(f"1. Success: Created test user with ID={user_id}, Timezone=Asia/Kolkata")

        # 2. Test Daily Job Generation & Timezone Handling (UTC storage check)
        target_date = date(2026, 6, 25)
        print(f"2. Generating meal & hydration jobs for date={target_date}...")
        
        generate_meal_jobs_for_user(db, user, target_date)
        generate_hydration_jobs_for_user(db, user, target_date)
        db.expire_all()
        
        # Verify job exists and timezone logic
        # For breakfast: 8:00 AM local time = 2:30 AM UTC on the same day.
        breakfast_job = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.user_id == user_id,
            ScheduledNotificationJob.notification_type == "MEAL_REMINDER_BREAKFAST"
        ).first()
        
        assert breakfast_job is not None, "Breakfast scheduled job should be generated."
        print(f"   Success: Breakfast job found (key={breakfast_job.job_key})")
        
        # Verify scheduled_for is timezone-aware UTC
        assert breakfast_job.scheduled_for.tzinfo is not None, "scheduled_for must be timezone-aware."
        expected_utc_dt = datetime.combine(target_date, time(2, 30)).replace(tzinfo=timezone.utc)
        
        # Make sure the offset matches
        assert breakfast_job.scheduled_for.astimezone(timezone.utc) == expected_utc_dt, \
            f"Expected {expected_utc_dt}, got {breakfast_job.scheduled_for.astimezone(timezone.utc)}"
        print("   Success: Timezone conversion correct! Local 8:00 AM resolved to 2:30 AM UTC.")

        # 3. Test Deduplication
        print("3. Testing Job Key Deduplication...")
        initial_jobs_count = db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.user_id == user_id).count()
        # Generate again: should do nothing (idempotency check)
        generate_meal_jobs_for_user(db, user, target_date)
        new_jobs_count = db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.user_id == user_id).count()
        
        assert initial_jobs_count == new_jobs_count, "Deduplication failed, generated duplicates."
        print(f"   Success: Idempotency check verified. No duplicate jobs created (count remains {initial_jobs_count}).")

        # 4. Test Inactivity Job Rescheduling
        print("4. Testing Inactivity Job Rescheduling...")
        reschedule_inactivity_reminder(db, user_id)
        
        inactivity_job1 = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.user_id == user_id,
            ScheduledNotificationJob.notification_type == "INACTIVITY_REMINDER",
            ScheduledNotificationJob.status == "PENDING"
        ).first()
        
        assert inactivity_job1 is not None, "Inactivity job not created."
        print(f"   Inactivity job 1 scheduled for: {inactivity_job1.scheduled_for} (status={inactivity_job1.status})")
        
        # Trigger reschedule (e.g. logging activity/sleep again)
        reschedule_inactivity_reminder(db, user_id)
        
        # Old one should be CANCELLED
        old_job = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.id == inactivity_job1.id
        ).first()
        assert old_job.status == "CANCELLED", f"Old inactivity job should be CANCELLED, got {old_job.status}"
        print("   Success: Old inactivity job correctly marked as CANCELLED.")
        
        # New one should be PENDING
        new_inactivity_job = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.user_id == user_id,
            ScheduledNotificationJob.notification_type == "INACTIVITY_REMINDER",
            ScheduledNotificationJob.status == "PENDING"
        ).first()
        assert new_inactivity_job is not None, "New inactivity job should be PENDING."
        assert new_inactivity_job.id != inactivity_job1.id, "Inactivity job ID should be different."
        print(f"   Success: New inactivity job scheduled for: {new_inactivity_job.scheduled_for}")

        # 5. Test Subscription Expiry Job Creation
        print("5. Testing Subscription Expiry Jobs...")
        # Get or create plan
        plan = db.query(Plan).first()
        if not plan:
            plan = Plan(name="Monthly Premium", description="Premium", price=99.00, duration_days=30, features="All")
            db.add(plan)
            db.commit()
            db.refresh(plan)
            
        payment = Payment(user_id=user_id, plan_id=plan.id, amount=99.00, status="completed", razorpay_order_id="order_test_123")
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        sub = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            payment_id=payment.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="active"
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        
        generate_subscription_expiry_jobs(db, sub)
        
        expiry_jobs = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.user_id == user_id,
            ScheduledNotificationJob.notification_type.in_(["SUBSCRIPTION_EXPIRING", "SUBSCRIPTION_EXPIRED"])
        ).all()
        
        # Expect 4 warning jobs: 7 days, 3 days, 1 day, and expiry day
        assert len(expiry_jobs) == 4, f"Expected 4 subscription expiry warning jobs, got {len(expiry_jobs)}"
        print("   Success: 4 subscription warning jobs created successfully.")

        # 6. Test Worker execution & Delivery Tracking Updates
        print("6. Testing Notification Worker Execution & Delivery Tracking...")
        # Manually alter a job to make it due in the past
        breakfast_job.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()
        
        # Add a fake active device token for push tracking
        device = DeviceToken(
            user_id=user_id,
            device_token="test_fcm_token_999",
            platform="web",
            is_active=True
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
        # Process pending jobs
        await process_pending_jobs()
        db.expire_all()
        
        # Job should be status='SENT'
        sent_job = db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.id == breakfast_job.id).first()
        assert sent_job.status == "SENT", f"Expected job status to be SENT, got {sent_job.status}"
        assert sent_job.sent_at is not None, "sent_at timestamp should be recorded."
        print(f"   Success: Worker processed and marked job as {sent_job.status}.")
        
        # Verify custom tracking columns on the created in-app notification
        created_notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "MEAL_REMINDER_BREAKFAST"
        ).first()
        
        assert created_notif is not None, "Notification record should be created."
        assert created_notif.source_module == "scheduled_jobs", f"Expected source_module='scheduled_jobs', got {created_notif.source_module}"
        assert created_notif.delivery_status == "SENT", f"Expected delivery_status='SENT', got {created_notif.delivery_status}"
        # WebSocket or push sent flags should be updated
        print(f"   Success: Delivery status columns verified (delivery_status={created_notif.delivery_status}, source_module={created_notif.source_module}).")

        # 7. Test Device Token Failure Tracking & Deactivation
        print("7. Testing FCM Device Token failure tracking...")
        # Check current device state
        assert device.is_active is True, "Device should initially be active."
        
        # Simulate pushing to unregistered device token (returns failure)
        # Using a mock invalid send
        push_success = await push_service.send_to_user(
            db=db,
            user_id=user_id,
            title="Unregistered Token Test",
            body="This token should fail"
        )
        db.refresh(device)
        
        # UnregisteredError returned by FCM mock/integration should deactivate it
        # Since "test_fcm_token_999" is invalid, Firebase messaging.send will raise UnregisteredError (or transient error if mocked/offline)
        # Check tracking fields
        print(f"   Device token updated: active={device.is_active}, failure_count={device.failure_count}, last_failure={device.last_push_failure}")
        assert device.failure_count > 0 or not device.is_active, "Failure count should be incremented or token deactivated."
        print("   Success: Device token failure tracking works!")

        print("\n====================================================")
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("====================================================")

    except Exception as e:
        print(f"\nError: Verification Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        clean_test_user(db, test_email)
        db.close()

if __name__ == "__main__":
    asyncio.run(test_scheduled_notifications())
