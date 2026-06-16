import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from firebase_admin import messaging

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
    ) -> bool:
        """
        Sends a single push notification to a device token using Firebase Cloud Messaging (FCM).
        Returns True if successful, False if the token is unregistered/invalid and should be deactivated.
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
            return True
        except messaging.UnregisteredError as ue:
            logger.warning(f"FCM token unregistered/invalid. Token: {device_token[:15]}... | Error: {ue}")
            return False
        except Exception as e:
            logger.error(f"FCM push delivery failed for token {device_token[:15]}...: {e}")
            # Do not deactivate for transient network errors, only for explicit UnregisteredError
            return True

    @staticmethod
    async def send_to_user(
        db: Session,
        user_id: int,
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Retrieves all active device tokens for the user and sends push notifications to all of them.
        """
        active_tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == True
        ).all()

        if not active_tokens:
            logger.debug(f"No active device tokens found for user {user_id}. Skipping push.")
            return

        inactive_tokens = []
        for token_record in active_tokens:
            success = await PushNotificationService.send_push_notification(
                device_token=token_record.device_token,
                title=title,
                body=body,
                metadata=metadata
            )
            if not success:
                inactive_tokens.append(token_record)

        if inactive_tokens:
            try:
                for token_record in inactive_tokens:
                    token_record.is_active = False
                db.commit()
                logger.info(f"Deactivated {len(inactive_tokens)} invalid/expired FCM tokens for user {user_id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to commit token deactivation for user {user_id}: {e}")

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

        try:
            batch_response = messaging.send_multicast(message)
            logger.info(f"FCM multicast batch sent. Successes: {batch_response.success_count}, Failures: {batch_response.failure_count}")

            if batch_response.failure_count > 0:
                inactive_tokens = []
                for idx, resp in enumerate(batch_response.responses):
                    if not resp.success:
                        exception = resp.exception
                        if isinstance(exception, messaging.UnregisteredError):
                            inactive_tokens.append(device_tokens[idx])
                            logger.warning(f"FCM token invalid in multicast batch: {device_tokens[idx][:15]}...")

                if inactive_tokens:
                    try:
                        db.query(DeviceToken).filter(
                            DeviceToken.device_token.in_(inactive_tokens)
                        ).update({DeviceToken.is_active: False}, synchronize_session=False)
                        db.commit()
                        logger.info(f"Deactivated {len(inactive_tokens)} invalid FCM tokens from multicast batch")
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Failed to update inactive tokens from multicast batch: {e}")
        except Exception as e:
            logger.error(f"FCM multicast batch delivery failed: {e}")


# Global service instance
push_service = PushNotificationService()
