import logging
import asyncio
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.scheduled_job import ScheduledNotificationJob
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Retry intervals in minutes: 1st retry in 1m, 2nd in 5m, 3rd in 15m, 4th in 30m, 5th in 60m
RETRY_INTERVALS = [1, 5, 15, 30, 60]
MAX_RETRIES = 5
# Concurrency configuration (Fix 2) - env-configurable
MAX_CONCURRENT_JOBS = int(os.getenv("NOTIFICATION_WORKER_CONCURRENCY", "10"))
BATCH_SIZE = 50


async def process_single_job(job_id: int, semaphore: asyncio.Semaphore, db: Session):
    """Processes a single scheduled notification job using the shared batch session with a nested savepoint (Fix 3)."""
    async with semaphore:
        try:
            # Re-query within savepoint scope
            job = db.query(ScheduledNotificationJob).filter(
                ScheduledNotificationJob.id == job_id,
                ScheduledNotificationJob.status == "PROCESSING"
            ).first()

            if not job:
                return

            # Trigger delivery through NotificationService (which queues websocket and push entries)
            await notification_service.create_notification(
                db=db,
                user_id=job.user_id,
                title=job.title,
                message=job.message,
                notification_type=job.notification_type,
                priority="high" if job.notification_type in ["SUBSCRIPTION_EXPIRING", "SUBSCRIPTION_EXPIRED"] else "normal",
                metadata=job.notification_metadata,
                source_module="scheduled_jobs",
                delivery_status="PENDING",
                scheduled_for=job.scheduled_for
            )

            # Mark job as SENT
            job.status = "SENT"
            job.sent_at = datetime.now(timezone.utc)
            logger.info(f"[NOTIFICATION WORKER] Job {job.id} (key={job.job_key}) sent/queued successfully.")

        except Exception as e:
            logger.error(f"[NOTIFICATION WORKER] Queuing failed for job {job_id}: {e}")
            # On error, handle retry logic without rollback (outer caller handles rollback per-job)
            try:
                job_to_retry = db.query(ScheduledNotificationJob).filter(
                    ScheduledNotificationJob.id == job_id
                ).first()
                if job_to_retry:
                    job_to_retry.retry_count += 1
                    if job_to_retry.retry_count >= MAX_RETRIES:
                        job_to_retry.status = "FAILED"
                        logger.error(f"[NOTIFICATION WORKER] Job {job_id} reached max retries. Marked as FAILED.")
                    else:
                        interval_minutes = RETRY_INTERVALS[job_to_retry.retry_count - 1]
                        next_retry_time = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                        job_to_retry.status = "PENDING"
                        job_to_retry.scheduled_for = next_retry_time
                        logger.info(f"[NOTIFICATION WORKER] Rescheduled job {job_id} for retry #{job_to_retry.retry_count} at {next_retry_time}")
            except Exception as retry_err:
                logger.error(f"[NOTIFICATION WORKER] Failed to update retry status for job {job_id}: {retry_err}")


async def process_pending_jobs():
    """Query, lock, and process pending scheduled notification jobs using a single batch session (Fix 3)."""
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)

        # Lock and retrieve pending jobs that are due using FOR UPDATE SKIP LOCKED
        jobs = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.status == "PENDING",
            ScheduledNotificationJob.scheduled_for <= now_utc
        ).with_for_update(skip_locked=True).limit(BATCH_SIZE).all()

        if not jobs:
            return

        job_ids = [job.id for job in jobs]
        logger.info(f"[NOTIFICATION WORKER] Locked {len(jobs)} pending jobs to process.")

        # Mark all jobs as PROCESSING in a quick transaction
        for job in jobs:
            job.status = "PROCESSING"
        db.commit()

        # Process jobs concurrently using a bounded semaphore,
        # sharing the same db session (Fix 3) to reduce pool pressure.
        # Each job runs in the same transaction; we commit once at the end.
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
        tasks = [process_single_job(job_id, semaphore, db) for job_id in job_ids]
        await asyncio.gather(*tasks)

        # Single batch commit for all job status updates (Fix 5)
        db.commit()
        logger.info(f"[NOTIFICATION WORKER] Batch of {len(job_ids)} jobs committed.")

    except Exception as e:
        db.rollback()
        logger.error(f"[NOTIFICATION WORKER] Error in process_pending_jobs: {e}")
    finally:
        db.close()


async def start_notification_worker():
    """Startup task to initialize and run the notification processing loop."""
    logger.info("[NOTIFICATION WORKER] Starting worker loop...")
    while True:
        try:
            await process_pending_jobs()
        except Exception as e:
            logger.error(f"[NOTIFICATION WORKER] Error in notification worker loop: {e}")
        await asyncio.sleep(5)  # Poll every 5 seconds

