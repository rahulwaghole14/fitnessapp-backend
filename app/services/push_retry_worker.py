import logging
import asyncio
import os
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.push_retry_queue import PushRetryQueue
from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.models.push_delivery_log import PushDeliveryLog
from app.services.push_service import push_service

logger = logging.getLogger(__name__)

RETRY_INTERVALS = [1, 5, 15, 30, 60]  # in minutes
MAX_RETRIES = 5


async def process_push_retry_jobs():
    """Query, lock, and process pending push retry jobs using PostgreSQL row-level locking."""
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        
        # Safely poll and lock jobs due for retry
        jobs = db.query(PushRetryQueue).filter(
            PushRetryQueue.status == "PENDING",
            PushRetryQueue.next_retry_at <= now_utc
        ).with_for_update(skip_locked=True).limit(50).all()

        if not jobs:
            return

        logger.info(f"[PUSH RETRY WORKER] Locked {len(jobs)} pending push retry jobs to process.")

        for job in jobs:
            # Mark job as PROCESSING
            job.status = "PROCESSING"
            db.commit()

            # Retrieve associated token and notification
            token_record = db.query(DeviceToken).filter(DeviceToken.id == job.device_token_id).first()
            notification = db.query(Notification).filter(Notification.id == job.notification_id).first()

            if not token_record or not token_record.is_active:
                logger.warning(f"[PUSH RETRY WORKER] Token {job.device_token_id} is inactive or missing. Cancelling retry job {job.id}.")
                job.status = "FAILED"
                db.commit()
                continue

            if not notification:
                logger.warning(f"[PUSH RETRY WORKER] Notification {job.notification_id} is missing. Cancelling retry job {job.id}.")
                job.status = "FAILED"
                db.commit()
                continue

            # Format metadata
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

            fcm_payload = {
                "notification_id": str(notification.id),
                "type": str(notification.notification_type or ""),
                "deep_link": str(deep_link or ""),
                "screen": str(screen or ""),
                "metadata": json.dumps(notification.notification_metadata or {})
            }

            logger.info(f"[PUSH EVENT] retry_triggered | notification_id={notification.id} | user_id={notification.user_id} | token_id={token_record.id} | type={notification.notification_type}")

            try:
                # Dispatch push notification directly
                status = await push_service.send_push_notification(
                    db=db,
                    user_id=notification.user_id,
                    device_token_id=token_record.id,
                    device_token=token_record.device_token,
                    title=notification.title,
                    body=notification.message,
                    metadata=fcm_payload,
                    notification_id=notification.id,
                    notification_type=notification.notification_type,
                    platform=token_record.platform
                )

                if status == "SUCCESS":
                    token_record.last_push_success = datetime.now(timezone.utc)
                    token_record.failure_count = 0
                    
                    # Update notification status
                    notification.push_sent = True
                    notification.push_sent_at = datetime.now(timezone.utc)
                    notification.delivery_status = "SENT"
                    
                    job.status = "SENT"
                    db.commit()
                    logger.info(f"[PUSH RETRY WORKER] Retry job {job.id} sent successfully. User ID: {notification.user_id}, Token ID: {token_record.id}")
                
                elif status in ("UNREGISTERED", "SENDER_ID_MISMATCH", "INVALID_ARGUMENT"):
                    # Token invalidation (do not retry again)
                    token_record.last_push_failure = datetime.now(timezone.utc)
                    token_record.failure_count += 1
                    token_record.is_active = False
                    
                    job.status = "FAILED"
                    db.commit()
                    logger.info(f"[PUSH RETRY WORKER] Retry job {job.id} failed due to invalid token ({status}). Token marked inactive.")
                
                elif status == "FIREBASE_NOT_INITIALIZED":
                    # Keep as pending for next run, do not increment retry count, do not deactivate token
                    job.status = "PENDING"
                    job.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=5)
                    db.commit()
                    logger.warning(f"[PUSH RETRY WORKER] Firebase not initialized. Postponing retry job {job.id}.")
                
                else:  # TRANSIENT_FAILURE
                    # Update token history
                    token_record.last_push_failure = datetime.now(timezone.utc)
                    token_record.failure_count += 1
                    if token_record.failure_count >= 3:
                        token_record.is_active = False
                        logger.info(f"FCM token {token_record.device_token[:15]}... failed {token_record.failure_count} times, marked inactive.")

                    # Reschedule retry job
                    job.retry_count += 1
                    if job.retry_count >= MAX_RETRIES:
                        job.status = "FAILED"
                        logger.error(f"[PUSH RETRY WORKER] Retry job {job.id} reached max retries. Marked as FAILED.")
                    else:
                        interval_minutes = RETRY_INTERVALS[job.retry_count - 1]
                        next_retry = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                        job.status = "PENDING"
                        job.next_retry_at = next_retry
                        logger.info(f"[PUSH RETRY WORKER] Rescheduled retry job {job.id} for attempt #{job.retry_count} at {next_retry}")
                    
                    db.commit()

            except Exception as inner_err:
                db.rollback()
                logger.error(f"[PUSH RETRY WORKER] Unexpected error during retry job {job.id}: {inner_err}")
                
                # Reschedule job as fallback
                job.retry_count += 1
                if job.retry_count >= MAX_RETRIES:
                    job.status = "FAILED"
                else:
                    interval_minutes = RETRY_INTERVALS[job.retry_count - 1]
                    job.status = "PENDING"
                    job.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"[PUSH RETRY WORKER] Error in retry worker loop: {e}")
    finally:
        db.close()


async def start_push_retry_worker():
    """Startup task to initialize and run the push notification retry processing loop."""
    logger.info("[PUSH RETRY WORKER] Starting retry worker loop...")
    while True:
        try:
            await process_push_retry_jobs()
        except Exception as e:
            logger.error(f"[PUSH RETRY WORKER] Error in loop execution: {e}")
        await asyncio.sleep(60)  # Run check every minute
