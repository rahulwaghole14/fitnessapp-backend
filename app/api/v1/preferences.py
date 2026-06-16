from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user_id
from app.models.notification_preference import NotificationPreference
from app.schemas.notification import NotificationPreferenceResponse, NotificationPreferenceUpdate

logger = logging.getLogger(__name__)


def get_notification_preferences(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> NotificationPreferenceResponse:
    """
    Retrieves the notification preferences for the authenticated user.
    Creates default preferences if none exist.
    """
    try:
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()

        if not preferences:
            # Create default preferences record (all enabled by default)
            preferences = NotificationPreference(user_id=user_id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
            logger.info(f"Created default notification preferences for user {user_id}")

        return preferences
    except Exception as e:
        logger.error(f"Failed to fetch notification preferences for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notification preferences: {str(e)}"
        )


def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> NotificationPreferenceResponse:
    """
    Updates the notification preferences for the authenticated user.
    """
    try:
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()

        if not preferences:
            # Create default first before applying updates
            preferences = NotificationPreference(user_id=user_id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)

        # Apply update payload values
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(preferences, key, value)

        db.commit()
        db.refresh(preferences)
        logger.info(f"Updated notification preferences for user {user_id}")
        return preferences
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update notification preferences for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification preferences: {str(e)}"
        )
