import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.models.notification import Notification
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

MAX_CONCURRENT_DELIVERIES = 100
BATCH_SIZE = 50
POLL_INTERVAL = 1.0  # seconds


async def process_single_websocket_item(item_id: int, semaphore: asyncio.Semaphore):
    """Processes a single websocket delivery queue item concurrently."""
    async with semaphore:
        db = SessionLocal()
        try:
            # Query the queue item in this session
            item = db.query(NotificationDeliveryQueue).filter(
                NotificationDeliveryQueue.id == item_id,
                NotificationDeliveryQueue.status == "PROCESSING"
            ).first()

            if not item:
                return

            notification = db.query(Notification).filter(
                Notification.id == item.notification_id
            ).first()

            if not notification:
                logger.error(f"[WS WORKER] Notification {item.notification_id} not found for queue item {item.id}")
                item.status = "FAILED"
                db.commit()
                return

            user_id = item.user_id

            # Calculate unread count for the WebSocket payload
            unread_count = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_deleted == False
            ).count()

            event_payload = {
                "id": notification.id,
                "user_id": notification.user_id,
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type,
                "priority": notification.priority,
                "is_read": notification.is_read,
                "is_deleted": notification.is_deleted,
                "metadata": notification.notification_metadata,
                "created_at": notification.created_at.isoformat() if notification.created_at else datetime.utcnow().isoformat(),
                "read_at": notification.read_at.isoformat() if notification.read_at else None,
                "unread_count": unread_count
            }

            # Send through the websocket manager
            await websocket_manager.send_to_all_user_devices(
                user_id=user_id,
                event="NEW_NOTIFICATION",
                data=event_payload
            )

            # Update DB records upon success
            item.status = "SENT"
            item.delivered_at = datetime.now(timezone.utc)

            notification.websocket_sent = True
            notification.websocket_sent_at = datetime.now(timezone.utc)
            notification.delivery_status = "SENT"

            db.commit()
            logger.debug(f"[WS WORKER] Successfully delivered notification {notification.id} via WebSocket to user {user_id}")

        except Exception as e:
            db.rollback()
            logger.error(f"[WS WORKER] Error processing websocket queue item {item_id}: {e}")
            try:
                # Attempt to mark the item as FAILED
                item_to_fail = db.query(NotificationDeliveryQueue).filter(
                    NotificationDeliveryQueue.id == item_id
                ).first()
                if item_to_fail:
                    item_to_fail.status = "FAILED"
                    db.commit()
            except Exception as fail_err:
                db.rollback()
                logger.error(f"[WS WORKER] Failed to mark queue item {item_id} as FAILED: {fail_err}")
        finally:
            db.close()


async def process_pending_websocket_deliveries():
    """Poll, lock, and process pending WebSocket delivery queue entries."""
    db = SessionLocal()
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
            return

        item_ids = [item.id for item in queue_items]
        logger.info(f"[WS WORKER] Locked {len(queue_items)} websocket queue items to process.")

        # Mark as PROCESSING in a quick transaction to release DB-level lock early
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

    # Process items concurrently using the semaphore
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DELIVERIES)
    tasks = [process_single_websocket_item(item_id, semaphore) for item_id in item_ids]
    await asyncio.gather(*tasks)


async def start_websocket_delivery_worker():
    """Startup task to initialize and run the WebSocket delivery worker loop."""
    logger.info("[WS WORKER] Starting WebSocket delivery worker loop...")
    while True:
        try:
            await process_pending_websocket_deliveries()
        except Exception as e:
            logger.error(f"[WS WORKER] Error in WebSocket delivery worker loop: {e}")
        await asyncio.sleep(POLL_INTERVAL)
