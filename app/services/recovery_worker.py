import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, or_

from app.core.database import SessionLocal
from app.models.scheduled_job import ScheduledNotificationJob
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.core.leader_election import scheduler_leader_lock

logger = logging.getLogger(__name__)

STUCK_TIMEOUT_MINUTES = 15
POLL_INTERVAL_SECONDS = 300  # Check every 5 minutes


async def recover_stuck_tasks():
    """
    Scans the database for jobs or delivery tasks stuck in PROCESSING status
    and reverts them to PENDING to ensure crash recovery.
    """
    # Only the leader process handles recovery to avoid redundant DB pressure
    if not scheduler_leader_lock.is_leader:
        return

    logger.info("[RECOVERY WORKER] Starting stuck processing recovery scan...")
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        timeout_threshold = now_utc - timedelta(minutes=STUCK_TIMEOUT_MINUTES)

        # ── 1. Recover Stuck ScheduledNotificationJobs ────────────────────────
        # Jobs stuck in PROCESSING for more than 15 minutes
        stuck_jobs = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.status == "PROCESSING",
            ScheduledNotificationJob.processing_started_at <= timeout_threshold
        ).all()

        if stuck_jobs:
            logger.warning(f"[RECOVERY WORKER] Found {len(stuck_jobs)} stuck processing scheduled jobs. Reverting...")
            for job in stuck_jobs:
                job.retry_count += 1
                if job.retry_count >= 5:  # MAX_RETRIES = 5
                    job.status = "FAILED"
                    logger.error(f"[RECOVERY WORKER] Stuck job {job.id} (key={job.job_key}) exceeded max retries. Marked as FAILED.")
                else:
                    job.status = "PENDING"
                    # Reschedule slightly in the future (e.g. 1 minute)
                    job.scheduled_for = now_utc + timedelta(minutes=1)
                    logger.info(f"[RECOVERY WORKER] Reset job {job.id} (key={job.job_key}) to PENDING for retry #{job.retry_count}.")
            db.commit()

        # ── 2. Recover Stuck Delivery Queue Items ─────────────────────────────
        # Delivery queue items stuck in PROCESSING for more than 15 minutes
        stuck_deliveries = db.query(NotificationDeliveryQueue).filter(
            NotificationDeliveryQueue.status == "PROCESSING",
            NotificationDeliveryQueue.delivery_started_at <= timeout_threshold
        ).all()

        if stuck_deliveries:
            logger.warning(f"[RECOVERY WORKER] Found {len(stuck_deliveries)} stuck delivery queue items. Reverting...")
            for item in stuck_deliveries:
                item.status = "PENDING"
                item.retry_count += 1
                # Push retry delay back slightly
                item.next_retry_at = now_utc + timedelta(minutes=1)
                logger.info(f"[RECOVERY WORKER] Reset delivery item {item.id} (channel={item.channel}) to PENDING.")
            db.commit()

    except Exception as e:
        logger.error(f"[RECOVERY WORKER] Error during stuck recovery: {e}")
        db.rollback()
    finally:
        db.close()


async def start_recovery_worker():
    """Startup task to initialize and run the stuck job recovery worker loop."""
    logger.info("[RECOVERY WORKER] Starting recovery worker loop...")
    while True:
        try:
            await recover_stuck_tasks()
        except Exception as e:
            logger.error(f"[RECOVERY WORKER] Error in recovery loop: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
