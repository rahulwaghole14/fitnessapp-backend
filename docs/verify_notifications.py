"""
Verification Script for User Notification Upgrade
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.jwt_utils import create_access_token
from app.models.user import User
from app.models.sleep import SleepSession, UserDailySleep, UserMonthlySleep, UserYearlySleep
from app.models.refresh_token import RefreshToken
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan
from app.models.workout import Workout
from app.models.meal import Meal
from app.models.bmi_classification import BMIClassification
from app.models.explore_activity import ExploreActivity
from app.models.user_activity_log import UserActivityLog
from app.models.notification import Notification
from app.services.notification_service import notification_service

def verify_system():
    print("Starting User Notification System Verification...")
    db = SessionLocal()
    try:
        # Get test user
        user = db.query(User).first()
        if not user:
            print("Error: No user found in database. Run test_sleep_module.py first to create a test user.")
            return

        user_id = user.id
        print(f"Test User found: ID={user_id}, Username={user.username}")

        # Generate JWT Token for this user
        token = create_access_token(user_id)
        print(f"Generated JWT Access Token: {token[:20]}...{token[-20:]}")

        # Clean notifications for test user
        db.query(Notification).filter(Notification.user_id == user_id).delete()
        db.commit()
        print("Cleaned existing notifications for test user.")

        # 1. Test create_notification
        print("\nCreating a test notification...")
        notif = db.query(Notification).filter(Notification.user_id == user_id).first()
        assert notif is None

        # Call create_notification_sync synchronously
        notification_service.create_notification_sync(
            db=db,
            user_id=user_id,
            title="System Test Notification",
            message="This is a test notification to verify system upgrade.",
            notification_type="TEST_EVENT",
            priority="normal",
            metadata={"test_key": "test_value"}
        )
        
        # Verify it exists in database
        db.expire_all()
        notif = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == "TEST_EVENT"
        ).first()

        assert notif is not None, "Notification should be saved in database"
        assert notif.title == "System Test Notification"
        assert notif.is_read is False
        assert notif.notification_metadata == {"test_key": "test_value"}
        print(f"Notification successfully saved: ID={notif.id}, Title='{notif.title}', metadata={notif.notification_metadata}")

        # 2. Test mark read status
        print("\nTesting read status update...")
        unread_count_before = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False
        ).count()
        assert unread_count_before == 1

        # Mark read
        notif.is_read = True
        db.commit()
        db.refresh(notif)

        unread_count_after = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False
        ).count()
        assert unread_count_after == 0
        assert notif.is_read is True
        print("Successfully verified notification mark-as-read DB transaction!")

        print("\nALL VERIFICATIONS PASSED SUCCESSFULLY! The user notification system is fully operational.")

    except Exception as e:
        print(f"Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_system()
