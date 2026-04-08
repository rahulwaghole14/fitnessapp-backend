from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user_activity_log import UserActivityLog
from app.core.websocket_manager import websocket_manager
from app.core.database import get_db
from datetime import datetime
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
    "SUSPICIOUS_ACTIVITY"
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


# Create a singleton instance
notification_service = NotificationService()
