from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user_activity_log import UserActivityLog
from app.services.notification_service import notification_service, ADMIN_IMPORTANT_ACTIVITIES
from app.utils.activity_logger import time_ago
from .dependencies import get_current_admin


def get_notifications(
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to fetch"),
    activity_type: Optional[str] = Query(None, description="Filter by specific activity type"),
    include_read: bool = Query(False, description="Include read notifications (default: False - only unread)"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
) -> List[Dict[str, Any]]:
    """
    Get recent admin notifications (important activity logs).
    
    Args:
        limit: Number of notifications to fetch (default: 50, max: 100)
        activity_type: Optional filter for specific activity type
        include_read: Whether to include read notifications (default: False - only unread)
        db: Database session
        current_admin: Current authenticated admin
    
    Returns:
        List of notification objects with detailed information
    """
    try:
        # Build the query
        query = db.query(UserActivityLog)
        
        # Filter by activity type if specified
        if activity_type:
            query = query.filter(UserActivityLog.activity_type == activity_type)
        else:
            # Default to admin-important activities only
            query = query.filter(UserActivityLog.activity_type.in_(
                ADMIN_IMPORTANT_ACTIVITIES
            ))
        
        # Filter for unread notifications by default
        if not include_read:
            query = query.filter(UserActivityLog.is_read == False)
        
        # Order by created_at DESC and limit
        recent_logs = query.order_by(desc(UserActivityLog.created_at)).limit(limit).all()
        
        # Format the response
        notifications = []
        for log in recent_logs:
            notifications.append({
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "activity_type": log.activity_type,
                "description": log.description,
                "is_read": log.is_read,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "time_ago": time_ago(log.created_at),
                "is_admin_important": notification_service.is_admin_important_activity(log.activity_type)
            })
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch notifications: {str(e)}"
        )


def get_notification_stats(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get notification statistics for admin dashboard.
    
    Args:
        db: Database session
        current_admin: Current authenticated admin
    
    Returns:
        Dictionary with notification statistics
    """
    try:
        stats = notification_service.get_notification_stats(db)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch notification stats: {str(e)}"
        )


def get_activity_types(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
) -> List[str]:
    """
    Get all available activity types for filtering.
    
    Args:
        db: Database session
        current_admin: Current authenticated admin
    
    Returns:
        List of unique activity types
    """
    try:
        # Get all unique activity types
        activity_types = db.query(UserActivityLog.activity_type).distinct().all()
        return [activity_type[0] for activity_type in activity_types]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch activity types: {str(e)}"
        )


def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Mark a specific notification as read.
    
    Args:
        notification_id: ID of the notification to mark as read
        db: Database session
        current_admin: Current authenticated admin
    
    Returns:
        Success message with updated notification details
    """
    try:
        # Find the notification
        notification = db.query(UserActivityLog).filter(
            UserActivityLog.id == notification_id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=404,
                detail="Notification not found"
            )
        
        # Update is_read status
        notification.is_read = True
        db.commit()
        db.refresh(notification)
        
        return {
            "message": "Notification marked as read successfully",
            "notification_id": notification.id,
            "is_read": notification.is_read
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


def mark_all_notifications_as_read(
    activity_type: Optional[str] = Query(None, description="Filter by specific activity type"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Mark all notifications as read (optionally filtered by activity type).
    
    Args:
        activity_type: Optional filter for specific activity type
        db: Database session
        current_admin: Current authenticated admin
    
    Returns:
        Success message with count of marked notifications
    """
    try:
        # Build query for unread notifications
        query = db.query(UserActivityLog).filter(UserActivityLog.is_read == False)
        
        # Filter by activity type if specified
        if activity_type:
            query = query.filter(UserActivityLog.activity_type == activity_type)
        else:
            # Default to admin-important activities only
            query = query.filter(UserActivityLog.activity_type.in_(
                ADMIN_IMPORTANT_ACTIVITIES
            ))
        
        # Count unread notifications
        unread_count = query.count()
        
        if unread_count == 0:
            return {
                "message": "No unread notifications found",
                "marked_count": 0
            }
        
        # Mark all as read
        query.update({UserActivityLog.is_read: True}, synchronize_session=False)
        db.commit()
        
        return {
            "message": f"Successfully marked {unread_count} notifications as read",
            "marked_count": unread_count,
            "activity_type_filter": activity_type
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


def get_unread_notifications_count(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
) -> Dict[str, int]:
    """
    Get count of unread notifications.
    
    Args:
        db: Database session
        current_admin: Current authenticated admin
    
    Returns:
        Dictionary with unread notification count
    """
    try:
        # Count unread admin-important notifications
        unread_count = db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.is_read == False,
                UserActivityLog.activity_type.in_(
                    ADMIN_IMPORTANT_ACTIVITIES
                )
            )
        ).count()
        
        return {"unread_count": unread_count}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get unread notifications count: {str(e)}"
        )
