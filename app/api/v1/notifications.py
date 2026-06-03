from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user_id
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationMarkReadResponse,
    NotificationSuccessResponse
)
from app.core.websocket_manager import websocket_manager


def get_user_notifications(
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to fetch"),
    include_read: bool = Query(True, description="Include read notifications in the result"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Fetch user-specific in-app notifications.
    """
    try:
        # Build base filter (exclude deleted ones)
        filters = [
            Notification.user_id == user_id,
            Notification.is_deleted == False,
            Notification.is_read == False
        ]
        
        # Optionally filter for unread only
        if not include_read:
            filters.append(Notification.is_read == False)
            
        query = db.query(Notification).filter(and_(*filters))
        
        # Get count of filtered items
        total = query.count()
        
        # Order by created_at descending and paginate
        notifications = query.order_by(desc(Notification.created_at)).limit(limit).all()
        
        # Fetch global unread count
        unread_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False
        ).count()
        
        return NotificationListResponse(
            notifications=notifications,
            total=total,
            unread_count=unread_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user notifications: {str(e)}"
        )



def get_user_unread_count(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get the unread notifications count for the authenticated user.
    """
    try:
        unread_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False
        ).count()
        
        return UnreadCountResponse(unread_count=unread_count)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unread count: {str(e)}"
        )



async def mark_user_notification_as_read(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Mark a specific notification as read and trigger real-time synchronization.
    """
    try:
        notification = db.query(Notification).filter(
            Notification.id == id,
            Notification.user_id == user_id,
            Notification.is_deleted == False
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
            
        # Update fields if not already read
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)
            
        # Calculate updated unread count
        unread_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False
        ).count()
        
        # Broadcast real-time read synchronization frame to all active user devices
        try:
            await websocket_manager.send_to_all_user_devices(
                user_id=user_id,
                event="NOTIFICATION_READ",
                data={
                    "id": notification.id,
                    "is_read": True,
                    "unread_count": unread_count
                }
            )
        except Exception as ws_err:
            # Non-blocking WebSocket failure logging
            print(f"WebSocket user synchronization failed for notification read: {ws_err}")
            
        return NotificationMarkReadResponse(
            message="Notification marked as read successfully",
            notification_id=notification.id,
            is_read=notification.is_read
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )



async def mark_all_user_notifications_as_read(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Mark all unread notifications of the user as read and broadcast unread reset frame.
    """
    try:
        unread_query = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False
        )
        
        unread_count = unread_query.count()
        if unread_count == 0:
            return NotificationSuccessResponse(
                message="No unread notifications found",
                success=True
            )
            
        # Update all unread notifications to read
        unread_query.update(
            {
                Notification.is_read: True,
                Notification.read_at: datetime.utcnow()
            },
            synchronize_session=False
        )
        db.commit()
        
        # Broadcast sync frame
        try:
            await websocket_manager.send_to_all_user_devices(
                user_id=user_id,
                event="ALL_NOTIFICATIONS_READ",
                data={
                    "unread_count": 0
                }
            )
        except Exception as ws_err:
            print(f"WebSocket user synchronization failed for mark all read: {ws_err}")
            
        return NotificationSuccessResponse(
            message=f"Successfully marked {unread_count} notifications as read",
            success=True
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )



async def delete_user_notification(
    id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Soft-delete a user notification.
    """
    try:
        notification = db.query(Notification).filter(
            Notification.id == id,
            Notification.user_id == user_id,
            Notification.is_deleted == False
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
            
        notification.is_deleted = True
        db.commit()
        
        # Calculate updated unread count
        unread_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False
        ).count()
        
        # Broadcast soft-delete sync frame
        try:
            await websocket_manager.send_to_all_user_devices(
                user_id=user_id,
                event="NOTIFICATION_DELETED",
                data={
                    "id": notification.id,
                    "unread_count": unread_count
                }
            )
        except Exception as ws_err:
            print(f"WebSocket user synchronization failed for notification delete: {ws_err}")
            
        return NotificationSuccessResponse(
            message="Notification deleted successfully",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )
