from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user_activity_log import UserActivityLog
from app.models.notification import Notification
from app.core.websocket_manager import websocket_manager
from app.core.database import get_db
from datetime import datetime, timezone
from typing import Optional, List
import asyncio
import logging

logger = logging.getLogger(__name__)


# Important activity types that should trigger admin notifications
ADMIN_IMPORTANT_ACTIVITIES = {
    "USER_REGISTERED",
    "FAILED_LOGIN", 
    "SUBSCRIPTION_PURCHASED",
    "PROFILE_UPDATED",
    "PASSWORD_CHANGED",
    "ACCOUNT_DEACTIVATED",
    "PAYMENT_FAILED",
    "WORKOUT_COMPLETED",
    "GOAL_ACHIEVED",
    "SUSPICIOUS_ACTIVITY",
    "FEEDBACK_SUBMITTED"
}


class NotificationService:
    
    @staticmethod
    def is_admin_important_activity(activity_type: str) -> bool:
        """Check if an activity type is important for admin notifications."""
        return activity_type in ADMIN_IMPORTANT_ACTIVITIES
    
    @staticmethod
    async def send_notification_to_admins(activity_log: UserActivityLog):
        """
        Send a WebSocket notification to all connected admin clients.
        
        Args:
            activity_log: The UserActivityLog instance to broadcast
        """
        if not NotificationService.is_admin_important_activity(activity_log.activity_type):
            logger.debug(f"Activity {activity_log.activity_type} is not admin-important, skipping notification")
            return
        
        # Format the notification message using standardized event format
        notification_message = {
            "event": "NEW_NOTIFICATION",
            "data": {
                "id": activity_log.id,
                "type": activity_log.activity_type,
                "message": activity_log.description,
                "username": activity_log.username,
                "timestamp": activity_log.created_at.isoformat() if activity_log.created_at else datetime.utcnow().isoformat(),
                "user_id": activity_log.user_id,
                "is_read": activity_log.is_read
            }
        }
        
        try:
            # Broadcast to all admin connections using standardized event format
            await websocket_manager.broadcast_event("NEW_NOTIFICATION", notification_message["data"])
            logger.info(f"Admin notification sent for activity {activity_log.activity_type}: {activity_log.description}")
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
    
    @staticmethod
    def create_activity_log(
        db: Session,
        user_id: Optional[int],
        username: str,
        activity_type: str,
        description: str
    ) -> UserActivityLog:
        """
        Create a new activity log entry.
        
        Args:
            db: Database session
            user_id: Optional user ID
            username: Username
            activity_type: Type of activity
            description: Description of the activity
            
        Returns:
            Created UserActivityLog instance
        """
        activity_log = UserActivityLog(
            user_id=user_id,
            username=username,
            activity_type=activity_type,
            description=description
        )
        
        db.add(activity_log)
        db.commit()
        db.refresh(activity_log)
        
        logger.info(f"Activity log created: {activity_type} - {description}")
        return activity_log
    
    @staticmethod
    async def create_activity_and_notify(
        db: Session,
        user_id: Optional[int],
        username: str,
        activity_type: str,
        description: str
    ) -> UserActivityLog:
        """
        Create activity log and send WebSocket notification in one operation.
        
        Args:
            db: Database session
            user_id: Optional user ID
            username: Username
            activity_type: Type of activity
            description: Description of the activity
            
        Returns:
            Created UserActivityLog instance
        """
        # Create the activity log first
        activity_log = NotificationService.create_activity_log(
            db=db,
            user_id=user_id,
            username=username,
            activity_type=activity_type,
            description=description
        )
        
        # Send WebSocket notification asynchronously
        try:
            await NotificationService.send_notification_to_admins(activity_log)
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
            # Don't fail the whole operation if WebSocket fails
        
        return activity_log
    
    @staticmethod
    def get_recent_notifications(
        db: Session,
        limit: int = 50,
        activity_types: Optional[List[str]] = None
    ) -> List[UserActivityLog]:
        """
        Get recent activity logs for admin notifications.
        
        Args:
            db: Database session
            limit: Maximum number of records to return
            activity_types: Optional filter for specific activity types
            
        Returns:
            List of UserActivityLog instances
        """
        query = db.query(UserActivityLog)
        
        # Filter by activity types if specified
        if activity_types:
            query = query.filter(UserActivityLog.activity_type.in_(activity_types))
        else:
            # Default to admin-important activities
            query = query.filter(UserActivityLog.activity_type.in_(ADMIN_IMPORTANT_ACTIVITIES))
        
        # Order by created_at descending and limit
        return query.order_by(UserActivityLog.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_notification_stats(db: Session) -> dict:
        """
        Get statistics about notifications for admin dashboard.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with notification statistics
        """
        total_notifications = db.query(UserActivityLog).count()
        admin_notifications = db.query(UserActivityLog).filter(
            UserActivityLog.activity_type.in_(ADMIN_IMPORTANT_ACTIVITIES)
        ).count()
        
        # Get read/unread counts
        admin_unread = db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.activity_type.in_(ADMIN_IMPORTANT_ACTIVITIES),
                UserActivityLog.is_read == False
            )
        ).count()
        
        admin_read = admin_notifications - admin_unread
        
        # Get counts by activity type
        activity_counts = {}
        for activity_type in ADMIN_IMPORTANT_ACTIVITIES:
            total_count = db.query(UserActivityLog).filter(
                UserActivityLog.activity_type == activity_type
            ).count()
            unread_count = db.query(UserActivityLog).filter(
                and_(
                    UserActivityLog.activity_type == activity_type,
                    UserActivityLog.is_read == False
                )
            ).count()
            activity_counts[activity_type] = {
                "total": total_count,
                "unread": unread_count,
                "read": total_count - unread_count
            }
        
        return {
            "total_notifications": total_notifications,
            "admin_notifications": admin_notifications,
            "admin_read": admin_read,
            "admin_unread": admin_unread,
            "activity_counts": activity_counts,
            "active_connections": websocket_manager.get_connection_count()
        }

    @staticmethod
    def get_notification_priority(notification_type: str) -> str:
        high_types = {
            "PAYMENT_FAILED",
            "SUBSCRIPTION_EXPIRED",
            "SUBSCRIPTION_EXPIRING",
            "SUBSCRIPTION_PURCHASED"
        }
        low_types = {
            "WELCOME",
            "MEAL_REMINDER_BREAKFAST",
            "MEAL_REMINDER_LUNCH",
            "MEAL_REMINDER_DINNER",
            "HYDRATION_REMINDER",
            "INACTIVITY_REMINDER"
        }
        if notification_type in high_types:
            return "HIGH"
        elif notification_type in low_types:
            return "LOW"
        return "NORMAL"

    @staticmethod
    async def create_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[dict] = None,
        source_module: Optional[str] = None,
        delivery_status: Optional[str] = "PENDING",
        scheduled_for: Optional[datetime] = None
    ) -> Notification:
        """
        Centralized method to create user notifications, calculate unread count,
        and queue delivery tasks to the NotificationDeliveryQueue.
        """
        # Resolve priority level (Phase 6)
        db_priority = NotificationService.get_notification_priority(notification_type) if notification_type else priority.upper()

        # 1. Save notification to database
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=db_priority.lower(),
            notification_metadata=metadata,
            source_module=source_module,
            delivery_status="PENDING",
            push_sent=False,
            websocket_sent=False,
            created_at=datetime.utcnow()
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        logger.info(f"User notification created: id={notification.id}, user_id={user_id}, title='{title}'")

        # 2. Add delivery tasks to queue (Phase 2 & Phase 10)
        from app.models.notification_delivery_queue import NotificationDeliveryQueue
        
        # 2a. Queue WebSocket Delivery
        ws_task = NotificationDeliveryQueue(
            notification_id=notification.id,
            user_id=user_id,
            channel="WEBSOCKET",
            status="PENDING",
            priority=db_priority,
            scheduled_for=scheduled_for,
            created_at=datetime.utcnow()
        )
        db.add(ws_task)

        # 2b. Queue Push Delivery (Check static preferences first to save rows)
        try:
            from app.models.notification_preference import NotificationPreference
            pref = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).first()
            
            global_push = pref.push_notifications if pref else True
            
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
            
            category_attribute = category_map.get(notification_type)
            category_enabled = getattr(pref, category_attribute, True) if (pref and category_attribute) else True
            
            if global_push and category_enabled:
                push_task = NotificationDeliveryQueue(
                    notification_id=notification.id,
                    user_id=user_id,
                    channel="PUSH",
                    status="PENDING",
                    priority=db_priority,
                    scheduled_for=scheduled_for,
                    created_at=datetime.utcnow()
                )
                db.add(push_task)
        except Exception as e:
            logger.error(f"Failed to check preferences during push queueing: {e}")

        try:
            db.commit()
            logger.info(f"Queued delivery tasks for Notification ID: {notification.id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit notification queue tasks: {e}")

        return notification

    @staticmethod
    def create_notification_sync(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[dict] = None
    ):
        """
        Sync wrapper around create_notification. Safely schedules the notification coroutine
        on the running FastAPI event loop without blocking or loop collisions.
        """
        import asyncio
        coro = NotificationService.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            metadata=metadata
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            # Fallback for standalone scripts/tests where no running loop is present
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(coro)
                loop.close()
            except Exception as e:
                logger.error(f"Failed to run create_notification fallback: {e}")

    @staticmethod
    def check_and_trigger_sleep_notifications(db: Session, user_id: int, session):
        """
        Check sleep session duration and quality, and trigger appropriate notifications.
        """
        try:
            from app.models.user import User
            user = db.query(User).filter(User.id == user_id).first()
            sleep_goal = user.sleep_goal if (user and user.sleep_goal is not None) else 480
            
            # 1. Sleep Goal Achieved
            if session.duration_minutes >= sleep_goal:
                existing = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.notification_type == "SLEEP_GOAL_ACHIEVED"
                ).all()
                already_notified = any(
                    (n.notification_metadata or {}).get("sleep_session_id") == str(session.id)
                    for n in existing
                )
                if not already_notified:
                    NotificationService.create_notification_sync(
                        db=db,
                        user_id=user_id,
                        title="Sleep Goal Achieved 🌙",
                        message="Great job! You reached your sleep goal and are building healthy sleep habits.",
                        notification_type="SLEEP_GOAL_ACHIEVED",
                        priority="normal",
                        metadata={"sleep_session_id": str(session.id), "duration_minutes": session.duration_minutes, "sleep_goal": sleep_goal}
                    )
            
            # 2. Sleep Quality Achievement (score >= 90)
            if session.sleep_score >= 90:
                existing = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.notification_type == "SLEEP_ACHIEVEMENT"
                ).all()
                already_notified = any(
                    (n.notification_metadata or {}).get("sleep_session_id") == str(session.id)
                    for n in existing
                )
                if not already_notified:
                    NotificationService.create_notification_sync(
                        db=db,
                        user_id=user_id,
                        title="Excellent Sleep! 🌙",
                        message="Your sleep quality was exceptional last night.",
                        notification_type="SLEEP_ACHIEVEMENT",
                        priority="normal",
                        metadata={"sleep_session_id": str(session.id), "sleep_score": session.sleep_score}
                    )
        except Exception as e:
            logger.error(f"Failed to check and trigger sleep notifications: {e}")

    @staticmethod
    def trigger_engagement_notifications(db: Session, user_id: int):
        """
        Trigger welcome and profile completed notifications for a user if they haven't been sent already.
        """
        try:
            # 1. Welcome Notification
            existing_welcome = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.notification_type == "WELCOME"
            ).first()
            if not existing_welcome:
                NotificationService.create_notification_sync(
                    db=db,
                    user_id=user_id,
                    title="Welcome to Fitness App 👋",
                    message="Your fitness journey starts now.",
                    notification_type="WELCOME",
                    priority="normal"
                )

            # 2. Profile Completed Notification
            existing_profile = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.notification_type == "PROFILE_COMPLETED"
            ).first()
            if not existing_profile:
                NotificationService.create_notification_sync(
                    db=db,
                    user_id=user_id,
                    title="Profile Completed ✅",
                    message="Your profile is ready. Let's start achieving your goals.",
                    notification_type="PROFILE_COMPLETED",
                    priority="normal"
                )
        except Exception as e:
            logger.error(f"Failed to trigger engagement notifications: {e}")


# Create a singleton instance
notification_service = NotificationService()
