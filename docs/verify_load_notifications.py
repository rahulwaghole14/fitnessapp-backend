import asyncio
import sys
import os
import json
from datetime import datetime, timezone, timedelta

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.notification import Notification
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.services.notification_service import notification_service
from app.services.websocket_delivery_worker import process_pending_websocket_deliveries
from app.services.push_delivery_worker import process_pending_push_deliveries
from app.services.notification_metrics_service import notification_metrics_service


async def main():
    print("Initializing Database Session...")
    db = SessionLocal()
    try:
        # 1. Ensure test user exists
        user = db.query(User).filter(User.username == "testuser_load").first()
        if not user:
            print("No test user found in database. Creating testuser_load...")
            user = User(
                username="testuser_load",
                email="testuser_load@example.com",
                password="fakehash"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            print(f"Found existing test user: {user.username} (ID: {user.id})")

        # 2. Clean up existing notifications & queue for a clean metrics slate
        print("Cleaning up old notifications and queue items...")
        db.query(NotificationDeliveryQueue).delete()
        db.query(Notification).delete()
        db.commit()

        # 3. Create 1000 notifications sequentially with different priorities/types
        print("Creating and queueing 1000 notifications of varying priorities...")
        start_queue_time = datetime.now(timezone.utc)
        for i in range(1000):
            # 1/3 high, 1/3 normal, 1/3 low
            if i % 3 == 0:
                n_type = "PAYMENT_FAILED"  # HIGH priority
            elif i % 3 == 1:
                n_type = "SLEEP_ANALYSIS"  # NORMAL priority
            else:
                n_type = "HYDRATION_REMINDER"  # LOW priority

            await notification_service.create_notification(
                db=db,
                user_id=user.id,
                title=f"Notification {i}",
                message=f"This is a stress test message for item {i}",
                notification_type=n_type,
                source_module="load_test"
            )
            if (i + 1) % 200 == 0:
                print(f"Queued {i + 1} notifications...")

        end_queue_time = datetime.now(timezone.utc)
        queue_duration = (end_queue_time - start_queue_time).total_seconds()
        print(f"Successfully queued 1000 notifications in {queue_duration:.2f} seconds.")

        # 4. Process delivery queue
        print("Running delivery workers to process the queue...")
        start_delivery_time = datetime.now(timezone.utc)
        
        pending_count = db.query(NotificationDeliveryQueue).filter(
            NotificationDeliveryQueue.status == "PENDING"
        ).count()
        print(f"Initial pending delivery queue size: {pending_count}")

        loop_count = 0
        # Process in batches of 50 items each, loop until all items processed or threshold reached
        while pending_count > 0 and loop_count < 100:
            await process_pending_websocket_deliveries()
            await process_pending_push_deliveries()
            
            pending_count = db.query(NotificationDeliveryQueue).filter(
                NotificationDeliveryQueue.status == "PENDING"
            ).count()
            loop_count += 1
            if loop_count % 5 == 0 or pending_count == 0:
                print(f"Loop {loop_count}: Remaining pending items: {pending_count}")

        end_delivery_time = datetime.now(timezone.utc)
        delivery_duration = (end_delivery_time - start_delivery_time).total_seconds()
        print(f"Processed all queue items in {delivery_duration:.2f} seconds.")

        # 5. Fetch and print metrics
        metrics = notification_metrics_service.get_performance_metrics(db)
        health = notification_metrics_service.get_worker_health_stats(db)

        print("\n" + "="*40)
        print("PERFORMANCE METRICS REPORT")
        print("="*40)
        print(json.dumps(metrics, indent=2))

        print("\n" + "="*40)
        print("WORKER HEALTH STATISTICS")
        print("="*40)
        print(json.dumps(health, indent=2))

    except Exception as e:
        print(f"Error during load verification: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
