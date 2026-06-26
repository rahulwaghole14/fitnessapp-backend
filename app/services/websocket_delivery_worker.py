import logging
import asyncio
import os
from datetime import datetime, timezone
from sqlalchemy import case, func

from app.core.database import SessionLocal
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.models.notification import Notification
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

# Concurrency configurations (Fix 2)
MAX_CONCURRENT_DELIVERIES = int(os.getenv("WEBSOCKET_WORKER_CONCURRENCY", "10"))
BATCH_SIZE = 50
POLL_INTERVAL = 1.0  # seconds


async def process_pending_websocket_deliveries():
    """Poll, lock, and process pending WebSocket delivery queue entries using decoupled transactions (Fix 3, 5, 6)."""
    db = SessionLocal()
    
    # 1. Fetch Phase: Lock items, load notifications and unread counts, then release DB session (Fix 3)
    try:
        # Select pending websocket queue items ordered by priority (HIGH -> NORMAL -> LOW) and created_at
        queue_items = db.query(NotificationDeliveryQueue).filter(
            NotificationDeliveryQueue.channel == "WEBSOCKET",
            NotificationDeliveryQueue.status == "PENDING"
        ).order_by(
            case(
                (NotificationDeliveryQueue.priority == "HIGH", 1),
                (NotificationDeliveryQueue.priority == "NORMAL", 2),
                (NotificationDeliveryQueue.priority == "LOW", 3),
                else_=4
            ).asc(),
            NotificationDeliveryQueue.created_at.asc()
        ).with_for_update(skip_locked=True).limit(BATCH_SIZE).all()

        if not queue_items:
            db.close()
            return

        logger.info(f"[WS WORKER] Locked {len(queue_items)} websocket queue items to process.")

        # Extract IDs
        user_ids = list(set([item.user_id for item in queue_items]))
        notification_ids = list(set([item.notification_id for item in queue_items]))

        # Bulk queries to avoid O(N) database trips
        notifications = db.query(Notification).filter(Notification.id.in_(notification_ids)).all()
        notif_map = {
            n.id: {
                "id": n.id,
                "user_id": n.user_id,
                "title": n.title,
                "message": n.message,
                "notification_type": n.notification_type,
                "priority": n.priority,
                "is_read": n.is_read,
                "is_deleted": n.is_deleted,
                "notification_metadata": n.notification_metadata,
                "created_at": n.created_at,
                "read_at": n.read_at
            } for n in notifications
        }

        # Batch unread counts for all users in the batch (Fix 6)
        unread_counts = db.query(
            Notification.user_id,
            func.count(Notification.id)
        ).filter(
            Notification.user_id.in_(user_ids),
            Notification.is_read == False,
            Notification.is_deleted == False
        ).group_by(Notification.user_id).all()
        
        unread_map = {user_id: count for user_id, count in unread_counts}

        items_data = [
            {
                "id": item.id,
                "notification_id": item.notification_id,
                "user_id": item.user_id
            } for item in queue_items
        ]

        # Mark all as PROCESSING in DB
        for item in queue_items:
            item.status = "PROCESSING"
            item.delivery_started_at = datetime.now(timezone.utc)
            
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[WS WORKER] Error claiming pending websocket queue items: {e}")
        return
    finally:
        db.close()

    # 2. Network Phase: Dispatch WebSocket messages concurrently
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DELIVERIES)

    async def dispatch_single_ws(item_data):
        async with semaphore:
            item_id = item_data["id"]
            user_id = item_data["user_id"]
            notif_id = item_data["notification_id"]

            notification = notif_map.get(notif_id)
            if not notification:
                logger.error(f"[WS WORKER] Notification {notif_id} not found for queue item {item_id}")
                return {"item_id": item_id, "status": "FAILED"}

            unread_count = unread_map.get(user_id, 0)

            event_payload = {
                "id": notification["id"],
                "user_id": notification["user_id"],
                "title": notification["title"],
                "message": notification["message"],
                "notification_type": notification["notification_type"],
                "priority": notification["priority"],
                "is_read": notification["is_read"],
                "is_deleted": notification["is_deleted"],
                "metadata": notification["notification_metadata"],
                "created_at": notification["created_at"].isoformat() if notification["created_at"] else datetime.utcnow().isoformat(),
                "read_at": notification["read_at"].isoformat() if notification["read_at"] else None,
                "unread_count": unread_count
            }

            try:
                # Send through websocket manager
                await websocket_manager.send_to_all_user_devices(
                    user_id=user_id,
                    event="NEW_NOTIFICATION",
                    data=event_payload
                )
                logger.debug(f"[WS WORKER] Successfully delivered notification {notif_id} via WebSocket to user {user_id}")
                return {"item_id": item_id, "notification_id": notif_id, "status": "SENT"}
            except Exception as e:
                logger.error(f"[WS WORKER] Error broadcasting websocket event for queue item {item_id}: {e}")
                return {"item_id": item_id, "notification_id": notif_id, "status": "FAILED"}

    tasks = [dispatch_single_ws(item_data) for item_data in items_data]
    results = await asyncio.gather(*tasks)

    # 3. Write Phase: Record results in a single commit (Fix 5)
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        for res in results:
            item_id = res["item_id"]
            status = res["status"]

            item = db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.id == item_id).first()
            if not item:
                continue

            item.status = status
            if status == "SENT":
                item.delivered_at = now_utc

                # Update main notification
                notification = db.query(Notification).filter(Notification.id == res["notification_id"]).first()
                if notification:
                    notification.websocket_sent = True
                    notification.websocket_sent_at = now_utc
                    notification.delivery_status = "SENT"

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[WS WORKER] Failed to write back batch statuses: {e}")
    finally:
        db.close()


async def start_websocket_delivery_worker():
    """Startup task to initialize and run the WebSocket delivery worker loop."""
    logger.info("[WS WORKER] Starting WebSocket delivery worker loop...")
    while True:
        try:
            await process_pending_websocket_deliveries()
        except Exception as e:
            logger.error(f"[WS WORKER] Error in WebSocket delivery worker loop: {e}")
        await asyncio.sleep(POLL_INTERVAL)
