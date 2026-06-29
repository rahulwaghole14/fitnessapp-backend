import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.notification import Notification
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.models.scheduled_job import ScheduledNotificationJob
from app.services.notification_service import notification_service
from app.core.leader_election import scheduler_leader_lock, AdvisoryLockManager

async def run_verification():
    print("====================================================")
    print("STARTING NOTIFICATION HARDENING VERIFICATION")
    print("====================================================")
    db = SessionLocal()
    
    # Get first user from DB to use valid foreign keys
    user = db.query(User).first()
    if not user:
        print("FAILED: No users exist in the database to run verification.")
        db.close()
        return
        
    test_user_id = user.id
    print(f"Using valid user ID: {test_user_id} for tests.")

    # Clean up test notifications/jobs if they exist from previous runs
    test_event_key = "test_duplicate_prevention_event"
    db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.user_id == test_user_id, NotificationDeliveryQueue.priority == "TEST_QUEUE").delete()
    db.query(Notification).filter(Notification.user_id == test_user_id, Notification.logical_event_id == test_event_key).delete()
    db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.user_id == test_user_id, ScheduledNotificationJob.notification_type == "TEST_STUCK").delete()
    db.commit()

    print("\n--- 1. Testing leader election advisory locks ---")
    lock_a = AdvisoryLockManager(lock_key=88889999)
    lock_b = AdvisoryLockManager(lock_key=88889999)
    
    acquired_a = await lock_a.acquire_leader_lock()
    print(f"Process A acquired leader lock (should be True): {acquired_a}")
    
    acquired_b = await lock_b.acquire_leader_lock()
    print(f"Process B acquired leader lock (should be False): {acquired_b}")
    
    lock_a.release_leader_lock()
    print("Process A released leader lock. Sleeping 0.5s for release propagation...")
    await asyncio.sleep(0.5)
    
    acquired_b_again = await lock_b.acquire_leader_lock()
    print(f"Process B acquired leader lock now (should be True): {acquired_b_again}")
    lock_b.release_leader_lock()

    print("\n--- 2. Testing unique constraint on notification logical_event_id ---")
    try:
        # Create first notification
        notif1 = await notification_service.create_notification(
            db=db,
            user_id=test_user_id,
            title="First Attempt",
            message="This should succeed",
            logical_event_id=test_event_key
        )
        db.commit()
        print("First notification created successfully.")
    except Exception as e:
        db.rollback()
        print(f"FAILED: First notification creation error: {e}")
        return

    print("\n--- 3. Testing unique constraint on notification logical_event_id duplication ---")
    try:
        # Attempt to create duplicate notification with same logical_event_id
        notif2 = await notification_service.create_notification(
            db=db,
            user_id=test_user_id,
            title="Second Attempt",
            message="This should fail due to unique constraint",
            logical_event_id=test_event_key
        )
        db.commit()
        print("FAILED: Allowed duplicate notification to be created.")
    except IntegrityError as ie:
        db.rollback()
        print(f"SUCCESS: Blocked duplicate notification creation via database constraint: {ie}")
    except Exception as e:
        db.rollback()
        print(f"FAILED: Unexpected error on duplicate creation: {e}")

    print("\n--- 4. Testing unique constraint on delivery queue (notification_id, channel) ---")
    try:
        # We delete all automatically created queue items for notif1 to do a manual test
        db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.notification_id == notif1.id).delete()
        db.commit()
        
        # Add WEBSOCKET channel manually
        ws_queue = NotificationDeliveryQueue(
            notification_id=notif1.id,
            user_id=test_user_id,
            channel="WEBSOCKET",
            status="PENDING",
            priority="TEST_QUEUE"
        )
        db.add(ws_queue)
        db.flush()
        print("Added first WEBSOCKET queue item.")
        
        # Add second WEBSOCKET queue item (duplicate)
        ws_queue_duplicate = NotificationDeliveryQueue(
            notification_id=notif1.id,
            user_id=test_user_id,
            channel="WEBSOCKET",
            status="PENDING",
            priority="TEST_QUEUE"
        )
        db.add(ws_queue_duplicate)
        db.flush()
        db.commit()
        print("FAILED: Allowed duplicate queue item to be added.")
    except IntegrityError as ie:
        db.rollback()
        print(f"SUCCESS: Blocked duplicate delivery queue task: {ie}")
    except Exception as e:
        db.rollback()
        print(f"FAILED: Unexpected error on duplicate queue: {e}")

    print("\n--- 5. Testing recovery worker stuck processing tasks ---")
    # Clean up any leftover test queue items first
    db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.notification_id == notif1.id).delete()
    db.commit()
    
    # Insert a stuck job in scheduled jobs (ensure we pass scheduled_for)
    stuck_job = ScheduledNotificationJob(
        user_id=test_user_id,
        notification_type="TEST_STUCK",
        title="Stuck Job",
        message="Stuck",
        status="PROCESSING",
        scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=20),
        processing_started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        job_key="stuck_job_test_key"
    )
    db.add(stuck_job)
    
    # Insert a stuck queue item
    stuck_queue = NotificationDeliveryQueue(
        notification_id=notif1.id,
        user_id=test_user_id,
        channel="PUSH",
        status="PROCESSING",
        priority="TEST_QUEUE",
        delivery_started_at=datetime.now(timezone.utc) - timedelta(minutes=20)
    )
    db.add(stuck_queue)
    db.commit()
    print("Inserted stuck processing job and queue item (20 minutes old).")

    # Run recovery simulation
    from app.services.recovery_worker import recover_stuck_tasks
    
    # Fake leader election status
    scheduler_leader_lock._is_leader = True
    print("Simulating that this process is leader for recovery worker...")
    await recover_stuck_tasks()
    
    # Verify they were reset
    db.refresh(stuck_job)
    db.refresh(stuck_queue)
    print(f"Stuck Job status after recovery (should be PENDING): {stuck_job.status}")
    print(f"Stuck Queue status after recovery (should be PENDING): {stuck_queue.status}")
    
    # Cleanup
    db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.user_id == test_user_id, NotificationDeliveryQueue.priority == "TEST_QUEUE").delete()
    db.query(Notification).filter(Notification.user_id == test_user_id, Notification.logical_event_id == test_event_key).delete()
    db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.user_id == test_user_id, ScheduledNotificationJob.notification_type == "TEST_STUCK").delete()
    db.commit()
    db.close()
    print("====================================================")
    print("HARDENING VERIFICATION RUN COMPLETE")
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_verification())
