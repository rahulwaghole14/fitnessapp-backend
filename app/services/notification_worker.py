import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import SessionLocal
from app.models.scheduled_job import ScheduledNotificationJob
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Retry intervals in minutes: 1st retry in 1m, 2nd in 5m, 3rd in 15m, 4th in 30m, 5th in 60m
RETRY_INTERVALS = [1, 5, 15, 30, 60]
MAX_RETRIES = 5


async def process_pending_jobs():
    """Query, lock, and process pending notification jobs."""
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        
        # Lock and retrieve pending jobs that are due using FOR UPDATE SKIP LOCKED for scalability/safety
        jobs = db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.status == "PENDING",
            ScheduledNotificationJob.scheduled_for <= now_utc
        ).with_for_update(skip_locked=True).limit(50).all()

        if not jobs:
            return

        logger.info(f"[NOTIFICATION WORKER] Locked {len(jobs)} pending jobs to process.")

        for job in jobs:
            # Mark job as PROCESSING
            job.status = "PROCESSING"
            db.commit()

            try:
                # Trigger delivery through existing NotificationService
                await notification_service.create_notification(
                    db=db,
                    user_id=job.user_id,
                    title=job.title,
                    message=job.message,
                    notification_type=job.notification_type,
                    priority="high" if job.notification_type in ["SUBSCRIPTION_EXPIRING", "SUBSCRIPTION_EXPIRED"] else "normal",
                    metadata=job.notification_metadata,
                    source_module="scheduled_jobs",
                    delivery_status="PENDING"
                )

                # Successful delivery
                job.status = "SENT"
                job.sent_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"[NOTIFICATION WORKER] Job {job.id} (key={job.job_key}) sent successfully.")

            except Exception as e:
                db.rollback()
                logger.error(f"[NOTIFICATION WORKER] Delivery failed for job {job.id}: {e}")
                
                # Retry logic
                job.retry_count += 1
                if job.retry_count >= MAX_RETRIES:
                    job.status = "FAILED"
                    logger.error(f"[NOTIFICATION WORKER] Job {job.id} reached max retries. Marked as FAILED.")
                else:
                    # Calculate next retry timestamp
                    interval_minutes = RETRY_INTERVALS[job.retry_count - 1]
                    next_retry_time = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                    
                    job.status = "PENDING"
                    job.scheduled_for = next_retry_time
                    logger.info(f"[NOTIFICATION WORKER] Rescheduled job {job.id} for retry #{job.retry_count} at {next_retry_time}")
                
                db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"[NOTIFICATION WORKER] Error processing pending jobs: {e}")
    finally:
        db.close()


async def start_notification_worker():
    """Startup task to initialize and run the notification processing loop."""
    logger.info("[NOTIFICATION WORKER] Starting worker loop...")
    while True:
        await process_pending_jobs()
        await asyncio.sleep(60)  # Run worker checks every minute
