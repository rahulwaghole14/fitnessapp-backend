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
from app.models.device_token import DeviceToken
from app.services.push_service import push_service
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

# Concurrency configurations (Fix 2)
MAX_CONCURRENT_DELIVERIES = int(os.getenv("PUSH_WORKER_CONCURRENCY", "10"))
BATCH_SIZE = 50
POLL_INTERVAL = 1.0  # seconds


async def process_pending_push_deliveries():
    """Poll, lock, and process pending Push delivery queue entries using decoupled transactions (Fix 3, 4, 5)."""
    db = SessionLocal()
    
    # 1. Fetch Phase: Lock items and load data, then release DB session immediately (Fix 4)
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
            db.close()
            return

        logger.info(f"[PUSH WORKER] Locked {len(queue_items)} push queue items to process.")

        # Extract IDs
        user_ids = list(set([item.user_id for item in queue_items]))
        notification_ids = list(set([item.notification_id for item in queue_items]))

        # Bulk queries to avoid O(N) database trips
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        notifications = db.query(Notification).filter(Notification.id.in_(notification_ids)).all()
        tokens = db.query(DeviceToken).filter(DeviceToken.user_id.in_(user_ids), DeviceToken.is_active == True).all()

        # Copy entity data to in-memory dictionary to support detached session processing
        user_map = {
            u.id: {
                "id": u.id,
                "last_app_activity": u.last_app_activity
            } for u in users
        }
        notification_map = {
            n.id: {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "notification_type": n.notification_type,
                "priority": n.priority,
                "notification_metadata": n.notification_metadata
            } for n in notifications
        }
        
        token_map = {}
        for t in tokens:
            if t.user_id not in token_map:
                token_map[t.user_id] = []
            token_map[t.user_id].append({
                "id": t.id,
                "device_token": t.device_token,
                "platform": t.platform
            })

        items_data = [
            {
                "id": item.id,
                "notification_id": item.notification_id,
                "user_id": item.user_id,
                "priority": item.priority
            } for item in queue_items
        ]

        # Mark all as PROCESSING in DB
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

    # 2. Network Phase: Execute external I/O outside active database transactions (Fix 4)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DELIVERIES)
    
    async def dispatch_single_push(item_data):
        async with semaphore:
            user_id = item_data["user_id"]
            notif_id = item_data["notification_id"]
            priority = item_data["priority"]
            
            # Smart push routing rules (Phase 5 specifications)
            is_ws_connected = len(websocket_manager.user_connections.get(user_id, [])) > 0
            is_offline = not is_ws_connected

            # User inactivity awareness
            threshold_minutes = int(os.getenv("PUSH_INACTIVITY_THRESHOLD_MINUTES", "20"))
            inactivity_delta = timedelta(minutes=threshold_minutes)
            now_utc = datetime.now(timezone.utc)

            is_inactive = True
            user_info = user_map.get(user_id)
            if user_info and user_info.get("last_app_activity"):
                last_act = user_info["last_app_activity"]
                if last_act.tzinfo is None:
                    last_act = last_act.replace(tzinfo=timezone.utc)
                is_inactive = (now_utc - last_act) > inactivity_delta

            should_push = False
            priority_clean = priority.lower()

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
                return {"item_id": item_data["id"], "status": "SKIPPED"}

            user_tokens = token_map.get(user_id, [])
            if not user_tokens:
                logger.debug(f"[PUSH WORKER] No active device tokens found for user {user_id}. Skipping push.")
                return {"item_id": item_data["id"], "status": "NO_TOKENS"}

            notif_info = notification_map.get(notif_id)
            if not notif_info:
                logger.error(f"[PUSH WORKER] Notification {notif_id} not found for queue item {item_data['id']}")
                return {"item_id": item_data["id"], "status": "NOTIF_NOT_FOUND"}

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
            screen = screen_map.get(notif_info["notification_type"])
            deep_link = f"fitnessapp://{screen}" if screen else None

            # Package structured FCM payload
            fcm_payload = {
                "notification_id": str(notif_id),
                "type": str(notif_info["notification_type"] or ""),
                "deep_link": str(deep_link or ""),
                "screen": str(screen or ""),
                "metadata": json.dumps(notif_info["notification_metadata"] or {})
            }

            token_results = []
            for token in user_tokens:
                # Dispatch network send concurrently without holding a DB connection (Fix 4)
                resp = await asyncio.to_thread(
                    push_service.send_fcm_network,
                    token["device_token"],
                    notif_info["title"],
                    notif_info["message"],
                    fcm_payload
                )
                token_results.append({
                    "token_record_id": token["id"],
                    "platform": token["platform"],
                    "status": resp["status"],
                    "error": resp.get("error"),
                    "message_id": resp.get("message_id")
                })

            any_success = any(tr["status"] == "SUCCESS" for tr in token_results)
            return {
                "item_id": item_data["id"],
                "notification_id": notif_id,
                "user_id": user_id,
                "status": "SENT" if any_success else "FAILED",
                "token_results": token_results,
                "notification_type": notif_info["notification_type"]
            }

    tasks = [dispatch_single_push(item_data) for item_data in items_data]
    results = await asyncio.gather(*tasks)

    # 3. Write Phase: Record delivery statuses and logs in a single batch transaction (Fix 5)
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        
        for res in results:
            item_id = res["item_id"]
            status = res["status"]

            # Query the queue item and corresponding notification to apply changes
            item = db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.id == item_id).first()
            if not item:
                continue

            if status == "SKIPPED":
                item.status = "SENT"
                item.delivered_at = now_utc
            elif status == "NO_TOKENS" or status == "NOTIF_NOT_FOUND":
                item.status = "FAILED"
            else:
                # Sent or failed due to token dispatches
                item.status = status
                if status == "SENT":
                    item.delivered_at = now_utc

                # Update main notification
                notification = db.query(Notification).filter(Notification.id == res["notification_id"]).first()
                if notification:
                    if status == "SENT":
                        notification.push_sent = True
                        notification.push_sent_at = now_utc
                    notification.delivery_status = "SENT" if status == "SENT" else "FAILED"

                # Save token dispatches logs and retry queues
                push_service.record_fcm_results_batch(
                    db=db,
                    user_id=res["user_id"],
                    notification_id=res["notification_id"],
                    notification_type=res["notification_type"],
                    results=res["token_results"]
                )

        db.commit()
        logger.info(f"[PUSH WORKER] Successfully updated status and logged batch outcomes.")
    except Exception as e:
        db.rollback()
        logger.error(f"[PUSH WORKER] Failed to write back batch statuses: {e}")
    finally:
        db.close()


async def start_push_delivery_worker():
    """Startup task to initialize and run the Push delivery worker loop."""
    logger.info("[PUSH WORKER] Starting Push delivery worker loop...")
    while True:
        try:
            await process_pending_push_deliveries()
        except Exception as e:
            logger.error(f"[PUSH WORKER] Error in Push delivery worker loop: {e}")
        await asyncio.sleep(POLL_INTERVAL)

