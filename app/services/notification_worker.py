import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.scheduled_job import ScheduledNotificationJob
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Retry intervals in minutes: 1st retry in 1m, 2nd in 5m, 3rd in 15m, 4th in 30m, 5th in 60m
RETRY_INTERVALS = [1, 5, 15, 30, 60]
MAX_RETRIES = 5
MAX_CONCURRENT_JOBS = 100
BATCH_SIZE = 50


async def process_single_job(job_id: int, semaphore: asyncio.Semaphore):
    """Processes a single scheduled notification job concurrently."""
    async with semaphore:
        db = SessionLocal()
        try:
            # Query the job in this task's session
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
            db.commit()
            logger.info(f"[NOTIFICATION WORKER] Job {job.id} (key={job.job_key}) sent/queued successfully.")

        except Exception as e:
            db.rollback()
            logger.error(f"[NOTIFICATION WORKER] Queuing failed for job {job_id}: {e}")
            
            # Retry logic
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
                        # Calculate next retry timestamp
                        interval_minutes = RETRY_INTERVALS[job_to_retry.retry_count - 1]
                        next_retry_time = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                        
                        job_to_retry.status = "PENDING"
                        job_to_retry.scheduled_for = next_retry_time
                        logger.info(f"[NOTIFICATION WORKER] Rescheduled job {job_id} for retry #{job_to_retry.retry_count} at {next_retry_time}")
                    db.commit()
            except Exception as retry_err:
                db.rollback()
                logger.error(f"[NOTIFICATION WORKER] Failed to update retry status for job {job_id}: {retry_err}")
        finally:
            db.close()


async def process_pending_jobs():
    """Query, lock, and process pending scheduled notification jobs using FOR UPDATE SKIP LOCKED."""
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        
        # Lock and retrieve pending jobs that are due using FOR UPDATE SKIP LOCKED for scalability/safety
        jobs = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.status == "PENDING",
            ScheduledNotificationJob.scheduled_for <= now_utc
        ).with_for_update(skip_locked=True).limit(BATCH_SIZE).all()

        if not jobs:
            return

        job_ids = [job.id for job in jobs]
        logger.info(f"[NOTIFICATION WORKER] Locked {len(jobs)} pending jobs to process.")

        # Mark jobs as PROCESSING in a quick transaction to release row-level locks early
        for job in jobs:
            job.status = "PROCESSING"
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"[NOTIFICATION WORKER] Error claiming pending jobs: {e}")
        return
    finally:
        db.close()

    # Process jobs concurrently using a bounded semaphore
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
    tasks = [process_single_job(job_id, semaphore) for job_id in job_ids]
    await asyncio.gather(*tasks)


async def start_notification_worker():
    """Startup task to initialize and run the notification processing loop."""
    logger.info("[NOTIFICATION WORKER] Starting worker loop...")
    while True:
        try:
            await process_pending_jobs()
        except Exception as e:
            logger.error(f"[NOTIFICATION WORKER] Error in notification worker loop: {e}")
        await asyncio.sleep(5)  # Run worker checks every 5 seconds (more responsive than 60s)
