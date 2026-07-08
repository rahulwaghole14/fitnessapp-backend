import logging
import asyncio
import os
import json
from datetime import datetime, timezone, timedelta, time
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func

from app.core.database import SessionLocal
from app.models.scheduled_job import ScheduledNotificationJob
from app.models.user import User
from app.models.notification_preference import NotificationPreference
from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.services.push_service import push_service

logger = logging.getLogger(__name__)

# Global checkpoint for hourly daily job generator fallback
LAST_DAILY_JOB_GENERATION_RUN = None
RETRY_INTERVALS = [1, 5, 15, 30, 60]  # in minutes


def should_run_daily_job_generator() -> bool:
    """Check if the hourly daily job generator fallback needs to run."""
    global LAST_DAILY_JOB_GENERATION_RUN
    now = datetime.now(timezone.utc)
    if LAST_DAILY_JOB_GENERATION_RUN is None:
        return True
    return (now - LAST_DAILY_JOB_GENERATION_RUN).total_seconds() >= 3600


def run_daily_job_generation(db: Session):
    """Fallback generator to run daily job generation for all active users."""
    global LAST_DAILY_JOB_GENERATION_RUN
    logger.info("[CRON] Running daily job generation fallback...")
    
    from app.services.notification_job_generator import (
        get_user_tz,
        generate_meal_jobs_for_user,
        generate_hydration_jobs_for_user
    )
    
    users = db.query(User).all()
    for user in users:
        user_tz = get_user_tz(user)
        user_local_time = datetime.now(user_tz)
        user_today = user_local_time.date()
        user_tomorrow = user_today + timedelta(days=1)
        
        for target_date in [user_today, user_tomorrow]:
            generate_meal_jobs_for_user(db, user, target_date)
            generate_hydration_jobs_for_user(db, user, target_date)
            
    LAST_DAILY_JOB_GENERATION_RUN = datetime.now(timezone.utc)
    logger.info(f"[CRON] Completed daily job generation fallback for {len(users)} users.")


def run_subscription_expiry_check(db: Session):
    """Check for expired subscriptions and mark them expired (replacing background scheduler loop)."""
    logger.info("[CRON] Running subscription expiry check...")
    from app.models.subscription import Subscription
    from app.services.notification_service import notification_service
    from datetime import date
    
    today = date.today()
    active_subscriptions = db.query(Subscription).filter(
        Subscription.status == "active",
        Subscription.end_date <= today
    ).with_for_update(skip_locked=True).all()
    
    if not active_subscriptions:
        return
        
    for sub in active_subscriptions:
        if sub.status != "active":
            continue
            
        sub.status = "expired"
        logical_key = f"subscription_{sub.id}_expired_{sub.end_date.strftime('%Y_%m_%d')}"
        
        try:
            # Reusing existing notification creation logic to create the expiry Notification & queue ws/push entries
            # Since create_notification is async, we run it in a loop or await it.
            # We will run this synchronously/async in process_pending_notifications
            # To avoid async issue in this helper, we define this as a helper that returns coroutines, or we wrap it.
            pass
        except Exception as inner_e:
            logger.error(f"[CRON] Failed to process subscription {sub.id} expiry: {inner_e}")


async def run_subscription_expiry_check_async(db: Session):
    """Async execution of subscription expiry checks."""
    logger.info("[CRON] Running subscription expiry check...")
    from app.models.subscription import Subscription
    from app.services.notification_service import notification_service
    from datetime import date
    
    today = date.today()
    active_subscriptions = db.query(Subscription).filter(
        Subscription.status == "active",
        Subscription.end_date <= today
    ).with_for_update(skip_locked=True).all()
    
    for sub in active_subscriptions:
        if sub.status != "active":
            continue
            
        sub.status = "expired"
        logical_key = f"subscription_{sub.id}_expired_{sub.end_date.strftime('%Y_%m_%d')}"
        
        try:
            await notification_service.create_notification(
                db=db,
                user_id=sub.user_id,
                title="Premium Subscription Expired",
                message="Your premium subscription has expired.",
                notification_type="SUBSCRIPTION_EXPIRED",
                priority="high",
                metadata={"subscription_id": sub.id, "end_date": str(sub.end_date)},
                logical_event_id=logical_key
            )
            db.commit()
            logger.info(f"[CRON] Subscription {sub.id} marked expired and notification queued.")
        except Exception as inner_e:
            db.rollback()
            logger.error(f"[CRON] Failed to process subscription {sub.id} expiry: {inner_e}")


def check_notification_preference(pref: Optional[NotificationPreference], notification_type: str) -> bool:
    """Validate global and type-specific preferences for the user."""
    if not pref:
        return True
    if not pref.push_notifications:
        return False
        
    category_map = {
        "WELCOME": "engagement_notifications",
        "PROFILE_COMPLETED": "engagement_notifications",
        "INACTIVITY_REMINDER": "engagement_notifications",
        "SLEEP_ANALYSIS": "sleep_notifications",
        "SLEEP_GOAL_ACHIEVED": "sleep_notifications",
        "SLEEP_ACHIEVEMENT": "sleep_notifications",
        "MEAL_REMINDER_BREAKFAST": "meal_reminders",
        "MEAL_REMINDER_LUNCH": "meal_reminders",
        "MEAL_REMINDER_DINNER": "meal_reminders",
        "HYDRATION_REMINDER": "hydration_reminders",
        "SUBSCRIPTION_PURCHASED": "subscription_notifications",
        "SUBSCRIPTION_EXPIRED": "subscription_notifications",
        "SUBSCRIPTION_EXPIRING": "subscription_notifications",
        "PAYMENT_FAILED": "subscription_notifications"
    }
    
    # Also support lowercase formats
    short_map = {
        "breakfast": "meal_reminders",
        "lunch": "meal_reminders",
        "dinner": "meal_reminders",
        "hydration": "hydration_reminders",
        "inactivity": "engagement_notifications",
        "subscription_expiry": "subscription_notifications"
    }
    
    attr = category_map.get(notification_type) or short_map.get(notification_type.lower())
    if attr:
        return getattr(pref, attr, True)
    return True


async def process_job(db: Session, job: ScheduledNotificationJob) -> bool:
    """Process a single scheduled notification job."""
    user = job.user
    if not user:
        job.status = "DEAD"
        job.failure_reason = "User does not exist"
        logger.error(f"[CRON] Failed notification {job.id}: User {job.user_id} does not exist.")
        return False

    # 1. Validate notification preferences
    pref = user.notification_preference
    if not check_notification_preference(pref, job.notification_type):
        logger.info(f"[CRON] Skipping job {job.id} (key={job.job_key}) for user {job.user_id} due to preferences.")
        job.status = "SENT"
        job.sent_at = datetime.now(timezone.utc)
        await schedule_next_recurring_notification(db, job)
        return True

    # 2. Validate active device tokens
    active_tokens = [t for t in user.device_tokens if t.is_active]
    if not active_tokens:
        logger.info(f"[CRON] Skipping job {job.id} (key={job.job_key}) for user {job.user_id}: No active device tokens.")
        job.status = "SENT"
        job.sent_at = datetime.now(timezone.utc)
        await schedule_next_recurring_notification(db, job)
        return True

    # 3. Create main Notification record in DB
    notification = db.query(Notification).filter(Notification.logical_event_id == job.job_key).first()
    if not notification:
        notification = Notification(
            user_id=job.user_id,
            title=job.title,
            message=job.message,
            notification_type=job.notification_type,
            priority="high" if job.notification_type in ["SUBSCRIPTION_EXPIRING", "SUBSCRIPTION_EXPIRED"] else "normal",
            notification_metadata=job.notification_metadata,
            source_module="cron_notifications",
            delivery_status="PENDING",
            push_sent=False,
            websocket_sent=False,
            logical_event_id=job.job_key,
            created_at=datetime.utcnow()
        )
        db.add(notification)
        db.flush()

    # 4. Prepare FCM Payload
    from app.services.push_retry_worker import SCREEN_MAP
    screen = SCREEN_MAP.get(job.notification_type)
    deep_link = f"fitnessapp://{screen}" if screen else None
    fcm_payload = {
        "notification_id": str(notification.id),
        "type": str(job.notification_type or ""),
        "deep_link": str(deep_link or ""),
        "screen": str(screen or ""),
        "metadata": json.dumps(job.notification_metadata or {})
    }

    # 5. Send FCM Notifications
    results = []
    for token in active_tokens:
        resp = await asyncio.to_thread(
            push_service.send_fcm_network,
            token.device_token,
            job.title,
            job.message,
            fcm_payload
        )
        resp.update({
            "token_record_id": token.id,
            "platform": token.platform
        })
        results.append(resp)

    # 6. Record FCM results in database
    any_success = push_service.record_fcm_results_batch(
        db=db,
        user_id=job.user_id,
        notification_id=notification.id,
        notification_type=job.notification_type,
        results=results
    )

    if any_success:
        job.status = "SENT"
        job.sent_at = datetime.now(timezone.utc)
        
        # Update notification object status
        notification.push_sent = True
        notification.push_sent_at = datetime.now(timezone.utc)
        notification.delivery_status = "SENT"
        
        logger.info(f"[CRON] Sent notification {job.id}")
        await schedule_next_recurring_notification(db, job)
        return True
    else:
        job.retry_count += 1
        error_msgs = "; ".join([r.get("error") for r in results if r.get("error")]) or "FCM delivery failed"
        
        # Update notification status
        notification.delivery_status = "FAILED"
        
        if job.retry_count >= 5:
            job.status = "DEAD"
            job.failure_reason = f"Max retries (5) reached. Last errors: {error_msgs}"
            logger.error(f"[CRON] Failed notification {job.id}: {job.failure_reason}")
        else:
            job.status = "FAILED"
            interval_minutes = RETRY_INTERVALS[min(job.retry_count - 1, len(RETRY_INTERVALS) - 1)]
            job.scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
            logger.warning(f"[CRON] Failed notification {job.id}. Rescheduled for retry #{job.retry_count} in {interval_minutes}m. Error: {error_msgs}")
            
        return False


async def schedule_next_recurring_notification(db: Session, job: ScheduledNotificationJob):
    """Schedule the next instance of a recurring notification job."""
    from app.services.notification_job_generator import (
        get_user_tz,
        MEAL_TEMPLATES,
        HYDRATION_SLOTS,
        HYDRATION_TEMPLATE,
        create_job_safe
    )
    
    user = job.user
    if not user:
        return
        
    notif_type = job.notification_type.lower()
    
    if "breakfast" in notif_type:
        details = MEAL_TEMPLATES["MEAL_REMINDER_BREAKFAST"]
        user_tz = get_user_tz(user)
        tomorrow = datetime.now(user_tz).date() + timedelta(days=1)
        local_dt = datetime.combine(tomorrow, time(details["hour"], details["minute"]))
        local_dt = user_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(timezone.utc)
        job_key = f"user_{user.id}_breakfast_{tomorrow.strftime('%Y_%m_%d')}"
        
        create_job_safe(
            db=db,
            user_id=user.id,
            notif_type="MEAL_REMINDER_BREAKFAST",
            title=details["title"],
            message=details["message"],
            metadata={"meal_date": str(tomorrow)},
            scheduled_for_utc=utc_dt,
            job_key=job_key
        )
        logger.info(f"[CRON] Scheduled next breakfast reminder for tomorrow: {utc_dt}")
        
    elif "lunch" in notif_type:
        details = MEAL_TEMPLATES["MEAL_REMINDER_LUNCH"]
        user_tz = get_user_tz(user)
        tomorrow = datetime.now(user_tz).date() + timedelta(days=1)
        local_dt = datetime.combine(tomorrow, time(details["hour"], details["minute"]))
        local_dt = user_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(timezone.utc)
        job_key = f"user_{user.id}_lunch_{tomorrow.strftime('%Y_%m_%d')}"
        
        create_job_safe(
            db=db,
            user_id=user.id,
            notif_type="MEAL_REMINDER_LUNCH",
            title=details["title"],
            message=details["message"],
            metadata={"meal_date": str(tomorrow)},
            scheduled_for_utc=utc_dt,
            job_key=job_key
        )
        logger.info(f"[CRON] Scheduled next lunch reminder for tomorrow: {utc_dt}")
        
    elif "dinner" in notif_type:
        details = MEAL_TEMPLATES["MEAL_REMINDER_DINNER"]
        user_tz = get_user_tz(user)
        tomorrow = datetime.now(user_tz).date() + timedelta(days=1)
        local_dt = datetime.combine(tomorrow, time(details["hour"], details["minute"]))
        local_dt = user_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(timezone.utc)
        job_key = f"user_{user.id}_dinner_{tomorrow.strftime('%Y_%m_%d')}"
        
        create_job_safe(
            db=db,
            user_id=user.id,
            notif_type="MEAL_REMINDER_DINNER",
            title=details["title"],
            message=details["message"],
            metadata={"meal_date": str(tomorrow)},
            scheduled_for_utc=utc_dt,
            job_key=job_key
        )
        logger.info(f"[CRON] Scheduled next dinner reminder for tomorrow: {utc_dt}")
        
    elif "hydration" in notif_type:
        current_slot = None
        if job.notification_metadata:
            current_slot = job.notification_metadata.get("slot")
            
        user_tz = get_user_tz(user)
        user_local_now = datetime.now(user_tz)
        
        if current_slot in HYDRATION_SLOTS:
            idx = HYDRATION_SLOTS.index(current_slot)
            if idx < len(HYDRATION_SLOTS) - 1:
                next_slot = HYDRATION_SLOTS[idx + 1]
                target_date = user_local_now.date()
            else:
                next_slot = HYDRATION_SLOTS[0]
                target_date = user_local_now.date() + timedelta(days=1)
        else:
            next_slot = HYDRATION_SLOTS[0]
            target_date = user_local_now.date() + timedelta(days=1)
            for slot in HYDRATION_SLOTS:
                sh, sm = map(int, slot.split(":"))
                slot_dt = datetime.combine(user_local_now.date(), time(sh, sm))
                slot_dt = user_tz.localize(slot_dt)
                if slot_dt > user_local_now:
                    next_slot = slot
                    target_date = user_local_now.date()
                    break
                    
        sh, sm = map(int, next_slot.split(":"))
        local_dt = datetime.combine(target_date, time(sh, sm))
        local_dt = user_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(timezone.utc)
        
        am_pm = "am" if sh < 12 else "pm"
        h_formatted = sh if sh <= 12 else sh - 12
        if h_formatted == 0:
            h_formatted = 12
        time_label = f"{h_formatted}{am_pm}"
        
        job_key = f"user_{user.id}_hydration_{time_label}_{target_date.strftime('%Y_%m_%d')}"
        
        create_job_safe(
            db=db,
            user_id=user.id,
            notif_type="HYDRATION_REMINDER",
            title=HYDRATION_TEMPLATE["title"],
            message=HYDRATION_TEMPLATE["message"],
            metadata={"slot": next_slot, "date": str(target_date)},
            scheduled_for_utc=utc_dt,
            job_key=job_key
        )
        logger.info(f"[CRON] Scheduled next hydration reminder ({next_slot}) for {target_date}: {utc_dt}")


async def process_pending_notifications() -> int:
    """Fetch and process all due scheduled notifications (main cron entrypoint)."""
    logger.info("[CRON] Started processing")
    
    # 1. Run daily job generator fallback in a separate session
    if should_run_daily_job_generator():
        temp_db = SessionLocal()
        try:
            run_daily_job_generation(temp_db)
        except Exception as jg_err:
            logger.error(f"[CRON] Error during daily job generation: {jg_err}")
        finally:
            temp_db.close()
            
    # 2. Run subscription expiry check in a separate session
    temp_db2 = SessionLocal()
    try:
        await run_subscription_expiry_check_async(temp_db2)
    except Exception as se_err:
        logger.error(f"[CRON] Error during subscription expiry check: {se_err}")
    finally:
        temp_db2.close()

    # 3. Main processing batch session
    db = SessionLocal()
    try:
        batch_size = int(os.getenv("CRON_BATCH_SIZE", "500"))
        now_utc = datetime.now(timezone.utc)
        
        # Query only the job IDs first using FOR UPDATE SKIP LOCKED to avoid PostgreSQL Outer Join locking errors
        jobs_to_lock = db.query(ScheduledNotificationJob.id).filter(
            or_(
                ScheduledNotificationJob.status == "PENDING",
                and_(
                    ScheduledNotificationJob.status == "FAILED",
                    ScheduledNotificationJob.retry_count < 5
                )
            ),
            ScheduledNotificationJob.scheduled_for <= now_utc
        ).with_for_update(skip_locked=True).limit(batch_size).all()
        
        if not jobs_to_lock:
            logger.info("[CRON] Found 0 jobs")
            logger.info("[CRON] Completed processing")
            return 0
            
        job_ids = [j.id for j in jobs_to_lock]
        
        # Query the full job objects with eager loading of user, preference, and device tokens
        from sqlalchemy.orm import selectinload
        jobs = db.query(ScheduledNotificationJob).options(
            joinedload(ScheduledNotificationJob.user).joinedload(User.notification_preference),
            joinedload(ScheduledNotificationJob.user).selectinload(User.device_tokens)
        ).filter(
            ScheduledNotificationJob.id.in_(job_ids)
        ).all()
            
        logger.info(f"[CRON] Found {len(jobs)} jobs")
        
        # Mark claimed jobs as PROCESSING in database
        for job in jobs:
            job.status = "PROCESSING"
            job.processing_started_at = now_utc
        db.flush()
        
        success_count = 0
        failed_count = 0
        
        for job in jobs:
            # Use database savepoint for each job to isolate transaction failures
            sp = db.begin_nested()
            try:
                is_success = await process_job(db, job)
                if is_success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                sp.rollback()
                logger.error(f"[CRON] Error processing job {job.id}: {e}")
                failed_count += 1
                
        # Perform single commit for all updates in the batch
        db.commit()
        logger.info(f"[CRON] Completed processing. Successfully processed: {success_count}, Failed/rescheduled: {failed_count}")
        return len(jobs)
        
    except Exception as e:
        db.rollback()
        logger.error(f"[CRON] Error in process_pending_notifications: {e}")
        raise e
    finally:
        db.close()
