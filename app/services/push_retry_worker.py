import logging
import asyncio
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from app.core.database import SessionLocal
from app.models.push_retry_queue import PushRetryQueue
from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.models.push_delivery_log import PushDeliveryLog
from app.services.push_service import push_service

logger = logging.getLogger(__name__)

RETRY_INTERVALS = [1, 5, 15, 30, 60]  # in minutes
MAX_RETRIES = 5
BATCH_SIZE = 50
# Env-configurable semaphore for concurrent FCM retries
MAX_CONCURRENT_RETRIES = int(os.getenv("PUSH_RETRY_WORKER_CONCURRENCY", "10"))

SCREEN_MAP = {
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


async def _dispatch_single_retry(
    job_id: int,
    token_str: str,
    title: str,
    body: str,
    fcm_payload: Dict[str, Any],
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """
    Dispatch a single FCM retry call without holding any DB session (Fix 6).
    Uses asyncio.to_thread so the blocking firebase call doesn't block the event loop (Fix 4).
    """
    async with semaphore:
        result = await asyncio.to_thread(
            push_service.send_fcm_network,
            token_str,
            title,
            body,
            fcm_payload
        )
        result["job_id"] = job_id
        return result


async def process_push_retry_jobs():
    """
    Query, lock, and process pending push retry jobs.
    
    Performance improvements:
    - Bulk-fetches token & notification data with IN queries (Fix 7).
    - Dispatches FCM calls concurrently outside DB session using asyncio.to_thread (Fix 4, Fix 6).
    - Applies all status updates in a single batch commit (Fix 5).
    """
    now_utc = datetime.now(timezone.utc)

    # ── Phase 1: Claim jobs ──────────────────────────────────────────────────
    db = SessionLocal()
    try:
        jobs: List[PushRetryQueue] = db.query(PushRetryQueue).filter(
            PushRetryQueue.status == "PENDING",
            PushRetryQueue.next_retry_at <= now_utc
        ).with_for_update(skip_locked=True).limit(BATCH_SIZE).all()

        if not jobs:
            return

        logger.info(f"[PUSH RETRY WORKER] Locked {len(jobs)} pending push retry jobs.")

        # Collect IDs for bulk queries
        job_ids = [j.id for j in jobs]
        token_ids = [j.device_token_id for j in jobs]
        notification_ids = [j.notification_id for j in jobs]

        # Mark all as PROCESSING in a single commit to release row-level locks
        for job in jobs:
            job.status = "PROCESSING"
        db.commit()

        # ── Bulk fetch associated data (Fix 7) ──────────────────────────────
        tokens = db.query(DeviceToken).filter(
            DeviceToken.id.in_(token_ids)
        ).all()
        token_map: Dict[int, DeviceToken] = {t.id: t for t in tokens}

        notifications = db.query(Notification).filter(
            Notification.id.in_(notification_ids)
        ).all()
        notification_map: Dict[int, Notification] = {n.id: n for n in notifications}

        # Reload jobs list from DB to work with refreshed state
        jobs = db.query(PushRetryQueue).filter(PushRetryQueue.id.in_(job_ids)).all()
        job_map: Dict[int, PushRetryQueue] = {j.id: j for j in jobs}

    except Exception as e:
        db.rollback()
        logger.error(f"[PUSH RETRY WORKER] Error claiming retry jobs: {e}")
        db.close()
        return
    finally:
        db.close()

    # ── Phase 2: Dispatch FCM concurrently OUTSIDE any DB session (Fix 6) ───
    dispatch_tasks = []
    # Track which jobs to skip (missing data)
    skip_jobs: Dict[int, str] = {}  # job_id -> reason

    for job in jobs:
        token_record = token_map.get(job.device_token_id)
        notification = notification_map.get(job.notification_id)

        if not token_record or not token_record.is_active:
            skip_jobs[job.id] = "INVALID_TOKEN"
            continue
        if not notification:
            skip_jobs[job.id] = "MISSING_NOTIFICATION"
            continue

        screen = SCREEN_MAP.get(notification.notification_type)
        deep_link = f"fitnessapp://{screen}" if screen else None
        fcm_payload = {
            "notification_id": str(notification.id),
            "type": str(notification.notification_type or ""),
            "deep_link": str(deep_link or ""),
            "screen": str(screen or ""),
            "metadata": json.dumps(notification.notification_metadata or {})
        }

        logger.info(
            f"[PUSH EVENT] retry_triggered | notification_id={notification.id} "
            f"| user_id={notification.user_id} | token_id={token_record.id} "
            f"| type={notification.notification_type}"
        )
        dispatch_tasks.append((job.id, token_record.device_token, notification.title, notification.message, fcm_payload))

    # Fire all FCM calls concurrently
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_RETRIES)
    fcm_coroutines = [
        _dispatch_single_retry(job_id, token_str, title, body, payload, semaphore)
        for job_id, token_str, title, body, payload in dispatch_tasks
    ]
    fcm_results_list = await asyncio.gather(*fcm_coroutines, return_exceptions=True)

    # Index results by job_id
    fcm_results: Dict[int, Dict[str, Any]] = {}
    for res in fcm_results_list:
        if isinstance(res, Exception):
            logger.error(f"[PUSH RETRY WORKER] Exception during FCM dispatch: {res}")
        elif isinstance(res, dict) and "job_id" in res:
            fcm_results[res["job_id"]] = res

    # ── Phase 3: Apply all result updates in a single batch session (Fix 5) ─
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)

        # Reload tokens we need to update
        token_ids_to_update = list({j.device_token_id for j in jobs})
        tokens_fresh = db.query(DeviceToken).filter(DeviceToken.id.in_(token_ids_to_update)).all()
        token_map_fresh: Dict[int, DeviceToken] = {t.id: t for t in tokens_fresh}

        # Reload notifications we need to update
        notif_ids_to_update = list({j.notification_id for j in jobs})
        notifs_fresh = db.query(Notification).filter(Notification.id.in_(notif_ids_to_update)).all()
        notif_map_fresh: Dict[int, Notification] = {n.id: n for n in notifs_fresh}

        # Reload jobs
        jobs_fresh = db.query(PushRetryQueue).filter(PushRetryQueue.id.in_(job_ids)).all()
        job_map_fresh: Dict[int, PushRetryQueue] = {j.id: j for j in jobs_fresh}

        # Handle skipped jobs (missing data)
        for job_id, reason in skip_jobs.items():
            job = job_map_fresh.get(job_id)
            if job:
                logger.warning(f"[PUSH RETRY WORKER] Job {job_id} skipped: {reason}. Marking FAILED.")
                job.status = "FAILED"

        # Apply FCM results
        for job_id, result in fcm_results.items():
            job = job_map_fresh.get(job_id)
            if not job:
                continue

            original_job = job_map.get(job_id)
            token_record = token_map_fresh.get(original_job.device_token_id) if original_job else None
            notification = notif_map_fresh.get(original_job.notification_id) if original_job else None

            status = result.get("status", "TRANSIENT_FAILURE")

            # Delivery log
            log_record = PushDeliveryLog(
                notification_id=job.notification_id,
                user_id=notification.user_id if notification else None,
                device_token_id=job.device_token_id,
                push_provider="FCM",
                status="SENT" if status == "SUCCESS" else "FAILED",
                error_message=result.get("error"),
                push_message_id=result.get("message_id"),
                notification_type=notification.notification_type if notification else None,
                created_at=now_utc,
                sent_at=now_utc if status == "SUCCESS" else None
            )
            db.add(log_record)

            if status == "SUCCESS":
                if token_record:
                    token_record.last_push_success = now_utc
                    token_record.failure_count = 0
                if notification:
                    notification.push_sent = True
                    notification.push_sent_at = now_utc
                    notification.delivery_status = "SENT"
                job.status = "SENT"
                logger.info(f"[PUSH RETRY WORKER] Retry job {job_id} delivered successfully.")

            elif status in ("UNREGISTERED", "SENDER_ID_MISMATCH", "INVALID_ARGUMENT"):
                if token_record:
                    token_record.last_push_failure = now_utc
                    token_record.failure_count = (token_record.failure_count or 0) + 1
                    token_record.is_active = False
                    logger.info(f"[PUSH RETRY WORKER] Token for job {job_id} invalidated ({status}).")
                job.status = "FAILED"

            elif status == "FIREBASE_NOT_INITIALIZED":
                # Postpone without incrementing retry count
                job.status = "PENDING"
                job.next_retry_at = now_utc + timedelta(minutes=5)
                logger.warning(f"[PUSH RETRY WORKER] Firebase not initialized. Postponing retry job {job_id}.")

            else:  # TRANSIENT_FAILURE or any exception string
                if token_record:
                    token_record.last_push_failure = now_utc
                    token_record.failure_count = (token_record.failure_count or 0) + 1
                    if token_record.failure_count >= 3:
                        token_record.is_active = False
                        logger.info(f"[PUSH RETRY WORKER] Token for job {job_id} failed {token_record.failure_count} times, marked inactive.")

                job.retry_count += 1
                if job.retry_count >= MAX_RETRIES:
                    job.status = "FAILED"
                    logger.error(f"[PUSH RETRY WORKER] Retry job {job_id} reached max retries. Marked as FAILED.")
                else:
                    interval_minutes = RETRY_INTERVALS[min(job.retry_count - 1, len(RETRY_INTERVALS) - 1)]
                    job.status = "PENDING"
                    job.next_retry_at = now_utc + timedelta(minutes=interval_minutes)
                    logger.info(f"[PUSH RETRY WORKER] Rescheduled retry job {job_id} for attempt #{job.retry_count}.")

        # Single batch commit for all updates (Fix 5)
        db.commit()
        logger.info(f"[PUSH RETRY WORKER] Batch of {len(jobs)} retry jobs committed.")

    except Exception as e:
        db.rollback()
        logger.error(f"[PUSH RETRY WORKER] Error applying retry results batch: {e}")
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
