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
    logger.info("[SCHEDULER] Running meal_reminder_job")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            user_tz, local_time = get_user_tz_and_local_time(user)
            user_today = local_time.date()
            user_current_time = local_time.time()
            
            for notif_type, details in MEAL_TEMPLATES.items():
                target_time = time(details["hour"], details["minute"])
                if user_current_time >= target_time:
                    # Check if already notified today
                    if not has_meal_notified_today(db, user.id, notif_type, user_today, user_tz):
                        await notification_service.create_notification(
                            db=db,
                            user_id=user.id,
                            title=details["title"],
                            message=details["message"],
                            notification_type=notif_type,
                            priority="normal",
                            metadata={"meal_date": str(user_today)}
                        )
                        logger.info(f"Sent {notif_type} to user {user.id}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Error in meal_reminder_job: {e}")
    finally:
        db.close()


async def hydration_reminder_job():
    """Check local times and send hydration reminders for configured slots."""
    logger.info("[SCHEDULER] Running hydration_reminder_job")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            user_tz, local_time = get_user_tz_and_local_time(user)
            user_today = local_time.date()
            user_current_time = local_time.time()
            
            for slot_str in HYDRATION_SLOTS:
                h, m = map(int, slot_str.split(":"))
                slot_time = time(h, m)
                if user_current_time >= slot_time:
                    if not has_hydration_notified_for_slot(db, user.id, user_today, slot_str, user_tz):
                        await notification_service.create_notification(
                            db=db,
                            user_id=user.id,
                            title=HYDRATION_TEMPLATE["title"],
                            message=HYDRATION_TEMPLATE["message"],
                            notification_type="HYDRATION_REMINDER",
                            priority="normal",
                            metadata={"slot": slot_str, "date": str(user_today)}
                        )
                        logger.info(f"Sent HYDRATION_REMINDER slot {slot_str} to user {user.id}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Error in hydration_reminder_job: {e}")
    finally:
        db.close()


async def subscription_expiry_job():
    """Query subscriptions, flag expired ones, and warn users 7 days / 1 day before expiration."""
    logger.info("[SCHEDULER] Running subscription_expiry_job")
    db = SessionLocal()
    try:
        # Get today's UTC/server date
        today = date.today()
        
        # Check active subscriptions
        active_subscriptions = db.query(Subscription).filter(Subscription.status == "active").all()
        
        for sub in active_subscriptions:
            user_id = sub.user_id
            expiry_date = sub.end_date
            
            # 1. Check if already expired
            if expiry_date <= today:
                # Update database status
                sub.status = "expired"
                db.commit()
                
                # Check duplicate notification
                existing = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.notification_type == "SUBSCRIPTION_EXPIRED"
                ).all()
                already_sent = any((n.notification_metadata or {}).get("subscription_id") == sub.id for n in existing)
                
                if not already_sent:
                    await notification_service.create_notification(
                        db=db,
                        user_id=user_id,
                        title="Premium Subscription Expired",
                        message="Your premium subscription has expired.",
                        notification_type="SUBSCRIPTION_EXPIRED",
                        priority="high",
                        metadata={"subscription_id": sub.id, "end_date": str(expiry_date)}
                    )
                    logger.info(f"Sent SUBSCRIPTION_EXPIRED for subscription {sub.id}")
            
            # 2. Check 7 days warning
            elif (expiry_date - today).days == 7:
                existing = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.notification_type == "SUBSCRIPTION_EXPIRING"
                ).all()
                already_sent = any(
                    (n.notification_metadata or {}).get("subscription_id") == sub.id and 
                    (n.notification_metadata or {}).get("days_left") == 7 
                    for n in existing
                )
                if not already_sent:
                    await notification_service.create_notification(
                        db=db,
                        user_id=user_id,
                        title="Premium Expiring Soon",
                        message="Your premium subscription will expire in 7 days.",
                        notification_type="SUBSCRIPTION_EXPIRING",
                        priority="high",
                        metadata={"subscription_id": sub.id, "days_left": 7, "end_date": str(expiry_date)}
                    )
                    logger.info(f"Sent 7-day SUBSCRIPTION_EXPIRING for subscription {sub.id}")
            
            # 3. Check 1 day warning
            elif (expiry_date - today).days == 1:
                existing = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.notification_type == "SUBSCRIPTION_EXPIRING"
                ).all()
                already_sent = any(
                    (n.notification_metadata or {}).get("subscription_id") == sub.id and 
                    (n.notification_metadata or {}).get("days_left") == 1 
                    for n in existing
                )
                if not already_sent:
                    await notification_service.create_notification(
                        db=db,
                        user_id=user_id,
                        title="Premium Ends Tomorrow",
                        message="Renew your subscription to continue enjoying premium benefits.",
                        notification_type="SUBSCRIPTION_EXPIRING",
                        priority="high",
                        metadata={"subscription_id": sub.id, "days_left": 1, "end_date": str(expiry_date)}
                    )
                    logger.info(f"Sent 1-day SUBSCRIPTION_EXPIRING for subscription {sub.id}")
                    
    except Exception as e:
        logger.error(f"[SCHEDULER] Error in subscription_expiry_job: {e}")
        db.rollback()
    finally:
        db.close()


async def inactivity_reminder_job():
    """Verify if a user has logged any activity in the last 3 days, and issue inactivity alerts."""
    logger.info("[SCHEDULER] Running inactivity_reminder_job")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        three_days_ago_date = three_days_ago.date()
        
        for user in users:
            user_id = user.id
            
            # 1. Check if user already received INACTIVITY_REMINDER in the last 3 days
            recent_inactivity_notif = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.notification_type == "INACTIVITY_REMINDER",
                Notification.created_at >= three_days_ago
            ).first()
            if recent_inactivity_notif:
                # Max 1 inactivity notification every 3 days. Skip!
                continue
                
            # 2. Check Daily Activities
            has_daily_activity = db.query(DailyActivity).filter(
                DailyActivity.user_id == user_id,
                DailyActivity.date >= three_days_ago_date
            ).first() is not None
            if has_daily_activity:
                continue
                
            # 3. Check Sleep Sessions
            has_sleep = db.query(SleepSession).filter(
                SleepSession.user_id == user_id,
                SleepSession.start_time >= three_days_ago,
                SleepSession.deleted_at.is_(None)
            ).first() is not None
            if has_sleep:
                continue
                
            # 4. Check other User Activity Logs (exclude inactivity reminders log and system logs)
            has_activity_log = db.query(UserActivityLog).filter(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= three_days_ago,
                UserActivityLog.activity_type != "inactivity_reminder"
            ).first() is not None
            if has_activity_log:
                continue
                
            # If we reached here, the user has been inactive for 3 days and has not been notified recently.
            await notification_service.create_notification(
                db=db,
                user_id=user_id,
                title="We Miss You 👋",
                message="You haven't logged activity recently. Let's get back on track.",
                notification_type="INACTIVITY_REMINDER",
                priority="normal"
            )
            logger.info(f"Sent INACTIVITY_REMINDER to user {user_id}")
            
    except Exception as e:
        logger.error(f"[SCHEDULER] Error in inactivity_reminder_job: {e}")
    finally:
        db.close()


async def start_scheduler():
    """Main centralized scheduler loop."""
    logger.info("[SCHEDULER] Starting centralized background loop...")
    while True:
        try:
            await meal_reminder_job()
        except Exception as e:
            logger.error(f"[SCHEDULER] Error during meal reminder task: {e}")
            
        try:
            await hydration_reminder_job()
        except Exception as e:
            logger.error(f"[SCHEDULER] Error during hydration reminder task: {e}")
            
        try:
            await subscription_expiry_job()
        except Exception as e:
            logger.error(f"[SCHEDULER] Error during subscription expiry task: {e}")
            
        try:
            await inactivity_reminder_job()
        except Exception as e:
            logger.error(f"[SCHEDULER] Error during inactivity reminder task: {e}")
            
        logger.info("[SCHEDULER] Job tick completed. Sleeping for 300 seconds...")
        await asyncio.sleep(300)
