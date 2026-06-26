import logging
import asyncio
import os
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import case

from app.core.database import SessionLocal
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.models.notification import Notification
from app.models.user import User
from app.services.push_service import push_service
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

MAX_CONCURRENT_DELIVERIES = 100
BATCH_SIZE = 50
POLL_INTERVAL = 1.0  # seconds


async def process_single_push_item(item_id: int, semaphore: asyncio.Semaphore):
    """Processes a single push delivery queue item concurrently."""
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
                logger.error(f"[PUSH WORKER] Notification {item.notification_id} not found for queue item {item.id}")
                item.status = "FAILED"
                db.commit()
                return

            user = db.query(User).filter(User.id == item.user_id).first()
            user_id = item.user_id

            # Evaluate smart push routing rules at execution time (Phase 5 of the specification)
            is_ws_connected = len(websocket_manager.user_connections.get(user_id, [])) > 0
            is_offline = not is_ws_connected

            # User inactivity awareness
            threshold_minutes = int(os.getenv("PUSH_INACTIVITY_THRESHOLD_MINUTES", "20"))
            inactivity_delta = timedelta(minutes=threshold_minutes)
            now_utc = datetime.now(timezone.utc)

            is_inactive = True
            if user and user.last_app_activity:
                last_act = user.last_app_activity
                if last_act.tzinfo is None:
                    last_act = last_act.replace(tzinfo=timezone.utc)
                is_inactive = (now_utc - last_act) > inactivity_delta

            # Smart routing decisions based on queue priority
            should_push = False
            priority_clean = item.priority.lower()

            if priority_clean == "high":
                should_push = True
            elif priority_clean == "normal":
                should_push = is_offline or is_inactive
            elif priority_clean == "low":
                should_push = is_inactive

            if not should_push:
                logger.info(
                    f"[PUSH WORKER] Skipping FCM push for user {user_id} based on Smart Routing "
                    f"(WS connected: {is_ws_connected}, Inactive: {is_inactive}, Priority: {priority_clean})"
                )
                # Mark as SENT because the delivery logic resolved it as complete without needing a push
                item.status = "SENT"
                item.delivered_at = datetime.now(timezone.utc)
                db.commit()
                return

            # Deep Link and Screen support
            screen_map = {
                "MEAL_REMINDER_BREAKFAST": "meals",
                "MEAL_REMINDER_LUNCH": "meals",
                "MEAL_REMINDER_DINNER": "meals",
                "HYDRATION_REMINDER": "hydration",
                "SLEEP_ANALYSIS": "sleep",
                "SLEEP_GOAL_ACHIEVED": "sleep",
                "SLEEP_ACHIEVEMENT": "sleep",
                "SUBSCRIPTION_PURCHASED": "premium",
                "SUBSCRIPTION_EXPIRED": "premium",
                "SUBSCRIPTION_EXPIRING": "premium",
                "PAYMENT_FAILED": "premium"
            }

            screen = screen_map.get(notification.notification_type)
            deep_link = f"fitnessapp://{screen}" if screen else None

            # Package structured FCM payload
            fcm_payload = {
                "notification_id": str(notification.id),
                "type": str(notification.notification_type or ""),
                "deep_link": str(deep_link or ""),
                "screen": str(screen or ""),
                "metadata": json.dumps(notification.notification_metadata or {})
            }

            logger.info(
                f"[PUSH WORKER] FCM push dispatch started | notification_id={notification.id} | "
                f"user_id={user_id} | type={notification.notification_type}"
            )

            # Trigger push notification delivery (sends concurrently to all active devices)
            push_success = await push_service.send_to_user(
                db=db,
                user_id=user_id,
                title=notification.title,
                body=notification.message,
                notification_id=notification.id,
                notification_type=notification.notification_type,
                metadata=fcm_payload
            )

            if push_success:
                item.status = "SENT"
                item.delivered_at = datetime.now(timezone.utc)

                notification.push_sent = True
                notification.push_sent_at = datetime.now(timezone.utc)
                notification.delivery_status = "SENT"
                logger.info(f"[PUSH WORKER] FCM push successfully dispatched for user {user_id}")
            else:
                # If sending failed (e.g. no active tokens, or all failed transiently and are in retry queue)
                item.status = "FAILED"
                logger.debug(f"[PUSH WORKER] FCM push dispatch failed (or queued for retry) for user {user_id}")

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"[PUSH WORKER] Error processing push queue item {item_id}: {e}")
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
                logger.error(f"[PUSH WORKER] Failed to mark queue item {item_id} as FAILED: {fail_err}")
        finally:
            db.close()


async def process_pending_push_deliveries():
    """Poll, lock, and process pending Push delivery queue entries."""
    db = SessionLocal()
    try:
        # Select pending push queue items ordered by priority (HIGH -> NORMAL -> LOW) and created_at
        queue_items = db.query(NotificationDeliveryQueue).filter(
            NotificationDeliveryQueue.channel == "PUSH",
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
        logger.info(f"[PUSH WORKER] Locked {len(queue_items)} push queue items to process.")

        # Mark as PROCESSING in a quick transaction to release DB lock early
        for item in queue_items:
            item.status = "PROCESSING"
            item.delivery_started_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"[PUSH WORKER] Error claiming pending push queue items: {e}")
        return
    finally:
        db.close()

    # Process items concurrently using the semaphore
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DELIVERIES)
    tasks = [process_single_push_item(item_id, semaphore) for item_id in item_ids]
    await asyncio.gather(*tasks)


async def start_push_delivery_worker():
    """Startup task to initialize and run the Push delivery worker loop."""
    logger.info("[PUSH WORKER] Starting Push delivery worker loop...")
    while True:
        try:
            await process_pending_push_deliveries()
        except Exception as e:
            logger.error(f"[PUSH WORKER] Error in Push delivery worker loop: {e}")
        await asyncio.sleep(POLL_INTERVAL)
