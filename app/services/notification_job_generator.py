import logging
import asyncio
import pytz
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_

from app.core.database import SessionLocal
from app.models.user import User
from app.models.scheduled_job import ScheduledNotificationJob
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan

logger = logging.getLogger(__name__)

# Constants
MEAL_TEMPLATES = {
    "MEAL_REMINDER_BREAKFAST": {
        "title": "Time for Breakfast! 🍳",
        "message": "Start your day fueled. Log your breakfast and stay on track.",
        "hour": 8,
        "minute": 0
    },
    "MEAL_REMINDER_LUNCH": {
        "title": "Time for Lunch! 🥗",
        "message": "Keep your energy up. Log your lunch and stay on track.",
        "hour": 13,
        "minute": 0
    },
    "MEAL_REMINDER_DINNER": {
        "title": "Time for Dinner! 🍲",
        "message": "Wind down and refuel. Log your dinner and stay on track.",
        "hour": 20,
        "minute": 0
    }
}

HYDRATION_SLOTS = ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"]
HYDRATION_TEMPLATE = {
    "title": "Hydration Reminder 💧",
    "message": "Take a moment to drink some water and stay hydrated."
}


def get_user_tz(user: User):
    """Resolve pytz timezone for user."""
    tz_name = user.timezone or "Asia/Kolkata"
    try:
        return pytz.timezone(tz_name)
    except Exception:
        return pytz.timezone("Asia/Kolkata")


def create_job_safe(db: Session, user_id: int, notif_type: str, title: str, message: str, 
                    metadata: dict, scheduled_for_utc: datetime, job_key: str):
    """Safely insert a job avoiding duplicates through unique key constraint."""
    # Check first to reduce unnecessary exceptions
    existing = db.query(ScheduledNotificationJob).filter(
        ScheduledNotificationJob.job_key == job_key
    ).first()
    if existing:
        return existing

    job = ScheduledNotificationJob(
        user_id=user_id,
        notification_type=notif_type,
        title=title,
        message=message,
        notification_metadata=metadata,
        scheduled_for=scheduled_for_utc,
        status="PENDING",
        job_key=job_key,
        retry_count=0
    )
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
        return job
    except IntegrityError:
        db.rollback()
        # Retrieve the job inserted concurrently
        return db.query(ScheduledNotificationJob).filter(
            ScheduledNotificationJob.job_key == job_key
        ).first()


def generate_meal_jobs_for_user(db: Session, user: User, target_date: date):
    """Generate daily meal scheduled jobs for a specific user and date."""
    user_tz = get_user_tz(user)
    date_str = target_date.strftime("%Y_%m_%d")

    for notif_type, details in MEAL_TEMPLATES.items():
        local_dt = datetime.combine(target_date, time(details["hour"], details["minute"]))
        local_dt = user_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(pytz.UTC)

        job_key = f"user_{user.id}_meal_reminder_{details['hour']}_{details['minute']}_{date_str}"
        # Fallback formatting as shown in requirement examples: user_25_breakfast_2026_06_25
        if "BREAKFAST" in notif_type:
            job_key = f"user_{user.id}_breakfast_{date_str}"
        elif "LUNCH" in notif_type:
            job_key = f"user_{user.id}_lunch_{date_str}"
        elif "DINNER" in notif_type:
            job_key = f"user_{user.id}_dinner_{date_str}"

        create_job_safe(
            db=db,
            user_id=user.id,
            notif_type=notif_type,
            title=details["title"],
            message=details["message"],
            metadata={"meal_date": str(target_date)},
            scheduled_for_utc=utc_dt,
            job_key=job_key
        )


def generate_hydration_jobs_for_user(db: Session, user: User, target_date: date):
    """Generate daily hydration scheduled jobs for a specific user and date."""
    user_tz = get_user_tz(user)
    date_str = target_date.strftime("%Y_%m_%d")

    for slot_str in HYDRATION_SLOTS:
        h, m = map(int, slot_str.split(":"))
        local_dt = datetime.combine(target_date, time(h, m))
        local_dt = user_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(pytz.UTC)

        # Key format matching: user_25_hydration_11am_2026_06_25
        # Convert hour to AM/PM string representation
        am_pm = "am" if h < 12 else "pm"
        h_formatted = h if h <= 12 else h - 12
        if h_formatted == 0:
            h_formatted = 12
        time_label = f"{h_formatted}{am_pm}"
        
        job_key = f"user_{user.id}_hydration_{time_label}_{date_str}"

        create_job_safe(
            db=db,
            user_id=user.id,
            notif_type="HYDRATION_REMINDER",
            title=HYDRATION_TEMPLATE["title"],
            message=HYDRATION_TEMPLATE["message"],
            metadata={"slot": slot_str, "date": str(target_date)},
            scheduled_for_utc=utc_dt,
            job_key=job_key
        )


def generate_subscription_expiry_jobs(db: Session, subscription: Subscription):
    """Automatically generate subscription expiry warnings when created or renewed."""
    user = db.query(User).filter(User.id == subscription.user_id).first()
    if not user:
        return

    user_tz = get_user_tz(user)
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    plan_name = plan.name if plan else "Premium"
    expiry_date = subscription.end_date

    # Expiry days offset configuration
    offsets = [
        {"days_before": 7, "notif_type": "SUBSCRIPTION_EXPIRING", "title": "Premium Expiring Soon", "message": f"Your premium subscription to {plan_name} will expire in 7 days."},
        {"days_before": 3, "notif_type": "SUBSCRIPTION_EXPIRING", "title": "Premium Expiring Soon", "message": f"Your premium subscription to {plan_name} will expire in 3 days. Renew to keep active!"},
        {"days_before": 1, "notif_type": "SUBSCRIPTION_EXPIRING", "title": "Premium Ends Tomorrow", "message": "Renew your subscription to continue enjoying premium benefits."},
        {"days_before": 0, "notif_type": "SUBSCRIPTION_EXPIRED", "title": "Premium Subscription Expired", "message": f"Your premium subscription to {plan_name} has expired."}
    ]

    # Cancel previous pending expiry jobs for this user/subscription to avoid conflicts or stale alerts on renewal
    db.query(ScheduledNotificationJob).filter(
        ScheduledNotificationJob.user_id == user.id,
        ScheduledNotificationJob.notification_type.in_(["SUBSCRIPTION_EXPIRING", "SUBSCRIPTION_EXPIRED"]),
        ScheduledNotificationJob.status == "PENDING"
    ).update({ScheduledNotificationJob.status: "CANCELLED"}, synchronize_session=False)
    db.commit()

    for offset in offsets:
        target_date = expiry_date - timedelta(days=offset["days_before"])
        
        # Schedule at 9:00 AM local time
        local_dt = datetime.combine(target_date, time(9, 0))
        local_dt = user_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(pytz.UTC)

        job_key = f"user_{user.id}_subscription_expiry_{subscription.id}_{offset['days_before']}_{expiry_date.strftime('%Y_%m_%d')}"
        
        create_job_safe(
            db=db,
            user_id=user.id,
            notif_type=offset["notif_type"],
            title=offset["title"],
            message=offset["message"],
            metadata={
                "subscription_id": subscription.id,
                "plan_name": plan_name,
                "days_left": offset["days_before"],
                "end_date": str(expiry_date)
            },
            scheduled_for_utc=utc_dt,
            job_key=job_key
        )


def reschedule_inactivity_reminder(db: Session, user_id: int):
    """
    Cancel previous inactivity jobs for a user and schedule a new inactivity job
    3 days later.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    # Cancel previous pending inactivity jobs for this user
    db.query(ScheduledNotificationJob).filter(
        ScheduledNotificationJob.user_id == user_id,
        ScheduledNotificationJob.notification_type == "INACTIVITY_REMINDER",
        ScheduledNotificationJob.status == "PENDING"
    ).update({ScheduledNotificationJob.status: "CANCELLED"}, synchronize_session=False)
    db.commit()

    # Schedule 3 days later
    now_utc = datetime.now(timezone.utc)
    scheduled_for = now_utc + timedelta(days=3)
    
    job_key = f"user_{user_id}_inactivity_{int(scheduled_for.timestamp())}"

    create_job_safe(
        db=db,
        user_id=user_id,
        notif_type="INACTIVITY_REMINDER",
        title="We Miss You 👋",
        message="You haven't logged activity recently. Let's get back on track.",
        metadata={},
        scheduled_for_utc=scheduled_for,
        job_key=job_key
    )


async def generate_daily_jobs():
    """Scan all users and generate meal and hydration scheduled notification jobs for today and tomorrow."""
    logger.info("[JOB GENERATOR] Starting daily job generation...")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        for user in users:
            # Generate for both today and tomorrow to handle timezone overlaps properly
            for target_date in [today, tomorrow]:
                generate_meal_jobs_for_user(db, user, target_date)
                generate_hydration_jobs_for_user(db, user, target_date)
        
        logger.info(f"[JOB GENERATOR] Completed job generation for {len(users)} users.")
    except Exception as e:
        logger.error(f"[JOB GENERATOR] Error during daily job generation: {e}")
    finally:
        db.close()


async def start_daily_job_generator():
    """Startup task to initialize and run daily scheduled job generation loop."""
    logger.info("[JOB GENERATOR] Starting daily job generator loop...")
    # Run immediately on startup to catch up on any missing schedule records
    await generate_daily_jobs()
    
    # Check hourly to dynamically schedule for new signups or timezone changes
    while True:
        await asyncio.sleep(3600)  # Check every hour
        await generate_daily_jobs()
