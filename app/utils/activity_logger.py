from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from app.models.user_activity_log import UserActivityLog
from app.services.notification_service import notification_service

# Define IST timezone using zoneinfo (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    # Fallback to pytz for older Python versions
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

# Activity type mapping for admin notifications
ACTIVITY_TYPE_MAPPING = {
    "signup": "USER_REGISTERED",
    "profile_update": "PROFILE_UPDATED", 
    "subscription_purchase": "SUBSCRIPTION_PURCHASED",
    "login": "USER_LOGIN",
    "failed_login": "FAILED_LOGIN",
    "password_change": "PASSWORD_CHANGED",
    "account_deactivate": "ACCOUNT_DEACTIVATED",
    "payment_failed": "PAYMENT_FAILED",
    "workout_complete": "WORKOUT_COMPLETED",
    "goal_achieved": "GOAL_ACHIEVED",
    "suspicious_activity": "SUSPICIOUS_ACTIVITY"
}


def log_activity(db: Session, user_id: Optional[int], username: str, activity_type: str, description: str, send_notification: bool = True) -> UserActivityLog:
    """
    Log user activity to the database.
    
    Args:
        db: Database session
        user_id: ID of the user performing the activity (nullable for system events)
        username: Username of the user
        activity_type: Type of activity (e.g., "signup", "profile_update", "subscription_purchase")
        description: Human-readable description (e.g., "Suraj signed up", "Suraj updated profile")
        send_notification: Whether to send WebSocket notification for admin-important activities
    
    Returns:
        UserActivityLog: The created activity log entry
    """
    # Map activity type to admin notification format
    mapped_activity_type = ACTIVITY_TYPE_MAPPING.get(activity_type, activity_type.upper())
    
    activity_log = UserActivityLog(
        user_id=user_id,
        username=username,
        activity_type=mapped_activity_type,
        description=description,
        created_at=datetime.utcnow()  # Store UTC internally
    )
    
    db.add(activity_log)
    db.commit()
    db.refresh(activity_log)
    
    # Send WebSocket notification if enabled and activity is admin-important
    if send_notification and notification_service.is_admin_important_activity(mapped_activity_type):
        try:
            # Create an event loop to run the async function
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(notification_service.send_notification_to_admins(activity_log))
            finally:
                loop.close()
        except Exception as e:
            # Log error but don't fail the activity logging
            print(f"Failed to send WebSocket notification: {e}")
    
    return activity_log


def time_ago(utc_time: Optional[datetime]) -> str:
    """
    Convert a UTC timestamp to a human-readable time difference in IST.
    
    Args:
        utc_time: UTC datetime from database
    
    Returns:
        str: Human-readable time difference (e.g., "just now", "2 min ago", "1 hr ago")
    """
    if not utc_time:
        return "Unknown time"
    
    try:
        # Ensure timestamp is timezone-aware (UTC)
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        
        # Convert UTC to IST
        ist_time = utc_time.astimezone(IST)
        
        # Get current IST time
        now_ist = datetime.now(IST)
        
        # Calculate time difference
        time_diff = now_ist - ist_time
        seconds = int(time_diff.total_seconds())
        
        # Apply formatting rules
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} min ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hr ago"
        elif seconds < 604800:  # 7 days
            days = seconds // 86400
            return f"{days} days ago"
        else:
            # Return formatted date for older timestamps
            return ist_time.strftime("%d %b %Y, %I:%M %p")
            
    except Exception as e:
        # Fallback to formatted timestamp if there's any error
        try:
            if utc_time.tzinfo is None:
                utc_time = utc_time.replace(tzinfo=timezone.utc)
            ist_time = utc_time.astimezone(IST)
            return ist_time.strftime("%d %b %Y, %I:%M %p")
        except:
            return "Unknown time"
