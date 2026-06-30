import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set sys.stdout output encoding to utf-8 to prevent windows stdout charmap codec errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.database import SessionLocal
from app.models.user import User
from app.models.notification import Notification
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.services.notification_service import notification_service
from app.schemas.notification import NotificationResponse

async def run_verification():
    print("====================================================")
    print("STARTING NOTIFICATION SCHEDULED_FOR TIME VERIFICATION")
    print("====================================================")
    db = SessionLocal()
    
    # Get first user from DB to use valid foreign keys
    user = db.query(User).first()
    if not user:
        print("FAILED: No users exist in the database to run verification.")
        db.close()
        return
        
    test_user_id = user.id
    print(f"Using user ID: {test_user_id} for tests.")

    # Clean up test notifications if they exist
    test_event_key_1 = "test_event_scheduled"
    test_event_key_2 = "test_event_manual"
    test_event_key_3 = "test_event_historical"
    db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.user_id == test_user_id).delete()
    db.query(Notification).filter(Notification.user_id == test_user_id, Notification.logical_event_id.in_([test_event_key_1, test_event_key_2, test_event_key_3])).delete()
    db.commit()

    # 1. Test creation with scheduled time
    print("\n--- Case A: Scheduled Notification (Meal / Hydration / etc.) ---")
    scheduled_time = datetime(2026, 6, 30, 20, 0, 0, tzinfo=timezone.utc)
    try:
        notif = await notification_service.create_notification(
            db=db,
            user_id=test_user_id,
            title="Time for Dinner!",
            message="Wind down and refuel.",
            notification_type="MEAL_REMINDER_DINNER",
            scheduled_for=scheduled_time,
            logical_event_id=test_event_key_1
        )
        db.commit()
        print("Notification created successfully.")
        
        # Serialize using Pydantic schema
        response_data = NotificationResponse.model_validate(notif)
        print("Serialized Pydantic Output:")
        print(response_data.model_dump_json(indent=2))
        
        # Verify fields
        assert response_data.scheduled_for is not None, "Error: scheduled_for is missing from schema serialization!"
        
        # Stored value is UTC or parsed datetime, let's verify equivalence
        notif_dt = response_data.scheduled_for.replace(tzinfo=timezone.utc) if response_data.scheduled_for.tzinfo is None else response_data.scheduled_for.astimezone(timezone.utc)
        assert notif_dt == scheduled_time, f"Error: scheduled_for mismatch! Expected {scheduled_time}, got {notif_dt}"
        assert response_data.metadata.get("scheduled_for") is not None, "Error: scheduled_for is missing from metadata dictionary!"
        print("SUCCESS: Scheduled notification time verified successfully.")
    except Exception as e:
        db.rollback()
        print(f"FAILED Case A: {e}")
        return

    # 2. Test creation without scheduled time (Manual Notification)
    print("\n--- Case B: Manual Notification (No scheduled time) ---")
    try:
        notif_manual = await notification_service.create_notification(
            db=db,
            user_id=test_user_id,
            title="Profile Updated",
            message="Your profile was updated.",
            notification_type="PROFILE_COMPLETED",
            scheduled_for=None,
            logical_event_id=test_event_key_2
        )
        db.commit()
        print("Notification created successfully.")
        
        # Serialize using Pydantic schema
        response_data_manual = NotificationResponse.model_validate(notif_manual)
        print("Serialized Pydantic Output:")
        print(response_data_manual.model_dump_json(indent=2))
        
        # Verify fields
        assert response_data_manual.scheduled_for is None, "Error: scheduled_for should be None for manual notifications!"
        if response_data_manual.metadata:
            assert "scheduled_for" not in response_data_manual.metadata, "Error: scheduled_for should not be present in manual metadata!"
        print("SUCCESS: Manual notification verified successfully.")
    except Exception as e:
        db.rollback()
        print(f"FAILED Case B: {e}")
        return

    # 3. Test reconstruction from historical metadata (no direct scheduled_for in metadata)
    print("\n--- Case C: Historical Notification Metadata Reconstruction ---")
    try:
        notif_hist = Notification(
            user_id=test_user_id,
            title="Hydration Reminder",
            message="Drink water",
            notification_type="HYDRATION_REMINDER",
            priority="low",
            notification_metadata={"slot": "11:00", "date": "2026-06-30"},
            logical_event_id=test_event_key_3
        )
        db.add(notif_hist)
        db.commit()
        
        # Serialize using Pydantic schema
        response_data_hist = NotificationResponse.model_validate(notif_hist)
        print("Serialized Pydantic Output:")
        print(response_data_hist.model_dump_json(indent=2))
        
        # Verify fields
        assert response_data_hist.scheduled_for is not None, "Error: scheduled_for should be reconstructed from metadata slot/date!"
        print(f"Reconstructed Scheduled Time: {response_data_hist.scheduled_for}")
        print("SUCCESS: Historical notification reconstruction verified successfully.")
        
        # Cleanup Case C
        db.delete(notif_hist)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"FAILED Case C: {e}")
        return

    # Clean up test notifications
    db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.user_id == test_user_id).delete()
    db.query(Notification).filter(Notification.user_id == test_user_id, Notification.logical_event_id.in_([test_event_key_1, test_event_key_2, test_event_key_3])).delete()
    db.commit()
    db.close()
    print("\n====================================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_verification())
