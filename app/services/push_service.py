import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from firebase_admin import messaging
from datetime import datetime, timezone

from app.core.firebase import initialize_firebase
from app.models.device_token import DeviceToken

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
initialize_firebase()


class PushNotificationService:
    @staticmethod
    async def send_push_notification(
        device_token: str,
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Sends a single push notification to a device token using Firebase Cloud Messaging (FCM).
        Returns:
            "SUCCESS": If sent successfully.
            "UNREGISTERED": If the token is unregistered/invalid (e.g. UnregisteredError).
            "TRANSIENT_FAILURE": If transient delivery/network error.
        """
        # Ensure metadata values are in string format for FCM data payload
        fcm_data = {}
        if metadata:
            for k, v in metadata.items():
                fcm_data[str(k)] = str(v)

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=fcm_data,
            token=device_token
        )

        try:
            response = messaging.send(message)
            logger.info(f"FCM push sent successfully. Response: {response}")
            return "SUCCESS"
        except messaging.UnregisteredError as ue:
            logger.warning(f"FCM token unregistered/invalid. Token: {device_token[:15]}... | Error: {ue}")
            return "UNREGISTERED"
        except Exception as e:
            logger.error(f"FCM push delivery failed for token {device_token[:15]}...: {e}")
            return "TRANSIENT_FAILURE"

    @staticmethod
    async def send_to_user(
        db: Session,
        user_id: int,
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Retrieves all active device tokens for the user, sends push notifications,
        updates failure/success counts, and deactivates invalid/failing ones.
        Returns True if at least one push was successfully sent, False otherwise.
        """
        active_tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == True
        ).all()

        if not active_tokens:
            logger.debug(f"No active device tokens found for user {user_id}. Skipping push.")
            return False

        any_success = False
        now_utc = datetime.now(timezone.utc)
        
        for token_record in active_tokens:
            status = await PushNotificationService.send_push_notification(
                device_token=token_record.device_token,
                title=title,
                body=body,
                metadata=metadata
            )
            
            if status == "SUCCESS":
                token_record.last_push_success = now_utc
                token_record.failure_count = 0
                any_success = True
            elif status == "UNREGISTERED":
                token_record.last_push_failure = now_utc
                token_record.failure_count += 1
                token_record.is_active = False
                logger.info(f"FCM token {token_record.device_token[:15]}... unregistered, marked inactive.")
            else:  # TRANSIENT_FAILURE
                token_record.last_push_failure = now_utc
                token_record.failure_count += 1
                if token_record.failure_count >= 3:
                    token_record.is_active = False
                    logger.info(f"FCM token {token_record.device_token[:15]}... failed {token_record.failure_count} times, marked inactive.")

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit token tracking updates for user {user_id}: {e}")

        return any_success

    @staticmethod
    async def send_to_multiple_devices(
        db: Session,
        device_tokens: List[str],
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Sends push notification to multiple device tokens and updates invalid ones.
        """
        if not device_tokens:
            return

        # Filter out duplicates
        device_tokens = list(set(device_tokens))

        fcm_data = {}
        if metadata:
            for k, v in metadata.items():
                fcm_data[str(k)] = str(v)

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=fcm_data,
            tokens=device_tokens
        )

        now_utc = datetime.now(timezone.utc)

        try:
            batch_response = messaging.send_multicast(message)
            logger.info(f"FCM multicast batch sent. Successes: {batch_response.success_count}, Failures: {batch_response.failure_count}")

            if len(batch_response.responses) > 0:
                for idx, resp in enumerate(batch_response.responses):
                    token = device_tokens[idx]
                    token_record = db.query(DeviceToken).filter(
                        DeviceToken.device_token == token
                    ).first()
                    
                    if not token_record:
                        continue
                        
                    if resp.success:
                        token_record.last_push_success = now_utc
                        token_record.failure_count = 0
                    else:
                        token_record.last_push_failure = now_utc
                        token_record.failure_count += 1
                        exception = resp.exception
                        
                        if isinstance(exception, messaging.UnregisteredError) or token_record.failure_count >= 3:
                            token_record.is_active = False
                            logger.info(f"Multicast FCM token {token[:15]}... invalid or failed too many times, marked inactive.")
                
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to commit multicast token tracking updates: {e}")
                    
        except Exception as e:
            logger.error(f"FCM multicast batch delivery failed: {e}")


# Global service instance
push_service = PushNotificationService()
