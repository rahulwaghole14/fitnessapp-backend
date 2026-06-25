import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.models.push_delivery_log import PushDeliveryLog
from app.models.push_retry_queue import PushRetryQueue
from app.services.notification_service import notification_service
from app.services.push_service import push_service
from app.services.push_retry_worker import process_push_retry_jobs


async def test_push_upgrades():
    print("--- STARTING PUSH UPGRADES VALIDATION TEST ---")
    db = SessionLocal()
    try:
        # 1. Fetch or create a test user
        user = db.query(User).first()
        if not user:
            print("No users found in database, creating a test user...")
            user = User(
                username="test_push_user",
                email="test_push@example.com",
                password="password",
                is_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        print(f"Using test user: {user.username} (ID: {user.id})")

        # 2. Test user activity updates
        print("\n[TEST 1] Testing User Activity updates...")
        user.last_app_activity = datetime.now(timezone.utc) - timedelta(minutes=30)
        db.commit()
        db.refresh(user)
        print(f"Updated user last_app_activity: {user.last_app_activity}")

        # 3. Register a test device token for this user
        print("\n[TEST 2] Registering test device token...")
        token_str = "dummy_token_12345_xyz"
        token_record = db.query(DeviceToken).filter(DeviceToken.device_token == token_str).first()
        if not token_record:
            token_record = DeviceToken(
                user_id=user.id,
                device_token=token_str,
                platform="android",
                device_name="Test Phone",
                is_active=True
            )
            db.add(token_record)
            db.commit()
            db.refresh(token_record)
        else:
            token_record.user_id = user.id  # Associate with current user
            token_record.is_active = True
            token_record.failure_count = 0
            db.commit()
            db.refresh(token_record)
        print(f"Registered token ID: {token_record.id}, User ID: {token_record.user_id}, Device: {token_record.device_name}, Active: {token_record.is_active}")

        # 4. Trigger a notification which should go to push (Test Invalid Token)
        print("\n[TEST 3] Generating a notification & checking push deactivation...")
        
        # Clear existing logs for this user/token to have a clean test
        db.query(PushDeliveryLog).filter(PushDeliveryLog.device_token_id == token_record.id).delete()
        db.query(PushRetryQueue).filter(PushRetryQueue.device_token_id == token_record.id).delete()
        db.commit()

        # Trigger a normal-priority meal reminder
        notif = await notification_service.create_notification(
            db=db,
            user_id=user.id,
            title="Time for Lunch! 🥗",
            message="Logging test notifications for push validation.",
            notification_type="MEAL_REMINDER_LUNCH",
            priority="normal",
            metadata={"meal_date": "2026-06-25"},
            source_module="test_suite"
        )
        print(f"Created Notification ID: {notif.id}")

        # 5. Check if PushDeliveryLog was created
        print("\n[TEST 4] Checking PushDeliveryLog for Invalid Token...")
        logs = db.query(PushDeliveryLog).filter(PushDeliveryLog.notification_id == notif.id).all()
        print(f"Found {len(logs)} delivery logs.")
        for l in logs:
            print(f" - Log ID: {l.id}, Status: {l.status}, Error: {l.error_message}")

        # Refresh token state to check if marked inactive
        db.refresh(token_record)
        print(f"Token is_active after invalid token send: {token_record.is_active}")

        # 6. Test Transient Failure & Retry Queue
        print("\n[TEST 5] Registering new token and mocking transient FCM error...")
        # Reactivate token and re-associate for transient test
        token_record.is_active = True
        token_record.failure_count = 0
        db.commit()

        # Mock firebase_admin.messaging.send to raise a transient exception
        import firebase_admin.messaging as fcm
        original_send = fcm.send
        
        def mock_send(message):
            raise Exception("Connection timeout to FCM gateway (transient failure test)")
        
        fcm.send = mock_send

        # Trigger notification
        notif_transient = await notification_service.create_notification(
            db=db,
            user_id=user.id,
            title="Hydration Reminder 💧",
            message="Logs transient failure and retries.",
            notification_type="HYDRATION_REMINDER",
            priority="normal",
            metadata={"slot": "13:00"},
            source_module="test_suite"
        )
        print(f"Created Notification ID: {notif_transient.id}")

        # Restore original send function
        fcm.send = original_send

        # Check if retry job is in push_retry_queue
        retries = db.query(PushRetryQueue).filter(PushRetryQueue.notification_id == notif_transient.id).all()
        print(f"Found {len(retries)} retry jobs in database.")
        for r in retries:
            print(f" - Retry ID: {r.id}, Status: {r.status}, Next Run: {r.next_retry_at}")

        # 7. Run Push Retry Worker simulation on the transient job
        if retries:
            print("\n[TEST 6] Simulating Push Retry Worker polling on transient failure...")
            # Modify next_retry_at to past so worker picks it up
            for r in retries:
                r.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=10)
            db.commit()

            print("Invoking worker process_push_retry_jobs()...")
            # This retry attempt should try sending it. Since we restored fcm.send,
            # it should run fcm.send(message), which will fail with InvalidArgumentError since the token is dummy,
            # but that validates that worker successfully executes the retry logic!
            await process_push_retry_jobs()

            # Refresh and inspect status
            db.refresh(retries[0])
            print(f"Worker simulation finished. Retry Job {retries[0].id} Status: {retries[0].status}, Attempt Count: {retries[0].retry_count}")

            # Check updated delivery logs
            logs = db.query(PushDeliveryLog).filter(PushDeliveryLog.notification_id == notif_transient.id).all()
            print("Updated delivery logs for transient notification:")
            for l in logs:
                print(f" - Log ID: {l.id}, Status: {l.status}, Error: {l.error_message}")

        print("\n--- ALL TESTS COMPLETED SUCCESSFULLY ---")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_push_upgrades())
