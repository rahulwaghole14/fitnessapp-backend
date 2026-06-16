from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user_id
from app.models.device_token import DeviceToken
from app.schemas.notification import DeviceTokenRegister, DeviceTokenUnregister, DeviceTokenResponse, NotificationSuccessResponse

logger = logging.getLogger(__name__)


def register_device_token(
    payload: DeviceTokenRegister,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> DeviceTokenResponse:
    """
    Registers or updates an FCM device token for the authenticated user.
    """
    # Verify platform is valid
    if payload.platform not in ("android", "ios", "web"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be one of: android, ios, web"
        )

    try:
        # Check if the token already exists
        existing_token = db.query(DeviceToken).filter(
            DeviceToken.device_token == payload.device_token
        ).first()

        if existing_token:
            # Update existing token properties (upsert)
            existing_token.user_id = user_id
            existing_token.platform = payload.platform
            existing_token.device_name = payload.device_name
            existing_token.is_active = True
            existing_token.last_seen = datetime.utcnow()
            db.commit()
            db.refresh(existing_token)
            logger.info(f"Updated device token registration for user {user_id}: {payload.device_token[:10]}...")
            return existing_token
        else:
            # Create a new device token record
            new_token = DeviceToken(
                user_id=user_id,
                device_token=payload.device_token,
                platform=payload.platform,
                device_name=payload.device_name,
                is_active=True,
                last_seen=datetime.utcnow()
            )
            db.add(new_token)
            db.commit()
            db.refresh(new_token)
            logger.info(f"Registered new device token for user {user_id}: {payload.device_token[:10]}...")
            return new_token
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to register device token for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register device token: {str(e)}"
        )


def unregister_device_token(
    payload: DeviceTokenUnregister,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> NotificationSuccessResponse:
    """
    Deactivates a device token by marking it is_active=False.
    """
    try:
        token_record = db.query(DeviceToken).filter(
            DeviceToken.device_token == payload.device_token,
            DeviceToken.user_id == user_id
        ).first()

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device token registration not found for the user"
            )

        token_record.is_active = False
        db.commit()
        logger.info(f"Deactivated device token for user {user_id}: {payload.device_token[:10]}...")
        return NotificationSuccessResponse(
            message="Device token unregistered successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to unregister device token for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister device token: {str(e)}"
        )
