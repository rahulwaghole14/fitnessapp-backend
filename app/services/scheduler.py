import asyncio
import logging
from datetime import datetime, date, time, timedelta
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import SessionLocal
from app.models.user import User
from app.models.notification import Notification
from app.models.activity import DailyActivity
from app.models.sleep import SleepSession
from app.models.user_activity_log import UserActivityLog
from app.models.subscription import Subscription
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Meal reminder payloads
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

# Hydration reminder settings
HYDRATION_SLOTS = ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"]
HYDRATION_TEMPLATE = {
    "title": "Hydration Reminder 💧",
    "message": "Take a moment to drink some water and stay hydrated."
}


def get_user_tz_and_local_time(user: User):
    """Get user's timezone object and current local datetime."""
    tz_name = user.timezone or "Asia/Kolkata"
    try:
        user_tz = pytz.timezone(tz_name)
    except Exception:
        user_tz = pytz.timezone("Asia/Kolkata")
    
    local_time = datetime.now(user_tz)
    return user_tz, local_time


def has_meal_notified_today(db: Session, user_id: int, notification_type: str, user_today: date, user_tz) -> bool:
    """Check if a meal notification was already sent to this user today."""
    since = datetime.utcnow() - timedelta(hours=36)
    notifs = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.notification_type == notification_type,
        Notification.created_at >= since
    ).all()
    for notif in notifs:
        created_utc = notif.created_at.replace(tzinfo=pytz.UTC)
        created_local = created_utc.astimezone(user_tz)
        if created_local.date() == user_today:
            return True
    return False


def has_hydration_notified_for_slot(db: Session, user_id: int, user_today: date, slot_str: str, user_tz) -> bool:
    """Check if a hydration notification was already sent to this user for the specified slot today."""
    since = datetime.utcnow() - timedelta(hours=36)
    notifs = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.notification_type == "HYDRATION_REMINDER",
        Notification.created_at >= since
    ).all()
    for notif in notifs:
        created_utc = notif.created_at.replace(tzinfo=pytz.UTC)
        created_local = created_utc.astimezone(user_tz)
        if created_local.date() == user_today:
            meta = notif.notification_metadata or {}
            if meta.get("slot") == slot_str:
                return True
    return False


async def meal_reminder_job():
    """Check local times and send breakfast/lunch/dinner reminders."""
    logger.info("[SCHEDULER] Running meal_reminder_job - Deprecated (Replaced by Scheduled Jobs Worker)")
    return


async def hydration_reminder_job():
    """Check local times and send hydration reminders for configured slots."""
    logger.info("[SCHEDULER] Running hydration_reminder_job - Deprecated (Replaced by Scheduled Jobs Worker)")
    return


async def subscription_expiry_job():
    """Query subscriptions, flag expired ones, and warn users 7 days / 1 day before expiration."""
    logger.info("[SCHEDULER] Running subscription_expiry_job - Deprecated (Replaced by Scheduled Jobs Worker)")
    db = SessionLocal()
    try:
        # Check active subscriptions and mark expired status only
        from app.models.subscription import Subscription
        from datetime import date
        today = date.today()
        active_subscriptions = db.query(Subscription).filter(Subscription.status == "active").all()
        for sub in active_subscriptions:
            if sub.end_date <= today:
                sub.status = "expired"
                db.commit()
                # Create the expired notification immediately (event-based fallback)
                from app.services.notification_service import notification_service
                await notification_service.create_notification(
                    db=db,
                    user_id=sub.user_id,
                    title="Premium Subscription Expired",
                    message="Your premium subscription has expired.",
                    notification_type="SUBSCRIPTION_EXPIRED",
                    priority="high",
                    metadata={"subscription_id": sub.id, "end_date": str(sub.end_date)}
                )
    except Exception as e:
        logger.error(f"[SCHEDULER] Error in subscription_expiry_job logic: {e}")
        db.rollback()
    finally:
        db.close()


async def inactivity_reminder_job():
    """Verify if a user has logged any activity in the last 3 days, and issue inactivity alerts."""
    logger.info("[SCHEDULER] Running inactivity_reminder_job - Deprecated (Replaced by Scheduled Jobs Worker)")
    return


async def start_scheduler():
    """Main centralized scheduler loop (kept for backwards compatibility)."""
    logger.info("[SCHEDULER] Starting deprecated centralized background loop...")
    while True:
        try:
            await subscription_expiry_job()
        except Exception as e:
            logger.error(f"[SCHEDULER] Error during subscription expiry cleanup: {e}")
        logger.info("[SCHEDULER] Job tick completed. Sleeping for 300 seconds...")
        await asyncio.sleep(300)
