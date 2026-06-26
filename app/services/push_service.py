import logging
import json
import asyncio
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from firebase_admin import messaging
from firebase_admin.exceptions import InvalidArgumentError
from firebase_admin.messaging import SenderIdMismatchError
import firebase_admin
from datetime import datetime, timezone, timedelta

from app.core.firebase import initialize_firebase
from app.models.device_token import DeviceToken
from app.models.push_delivery_log import PushDeliveryLog
from app.models.push_retry_queue import PushRetryQueue

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
initialize_firebase()


class PushNotificationService:
    @staticmethod
    async def send_push_notification(
        db: Session,
        user_id: int,
        device_token_id: int,
        device_token: str,
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        notification_id: Optional[int] = None,
        notification_type: Optional[str] = None,
        platform: Optional[str] = None
    ) -> str:
        """
        Sends a single push notification to a device token using Firebase Cloud Messaging (FCM).
        Records the attempt to push_delivery_logs.
        Returns:
            "SUCCESS": If sent successfully.
            "UNREGISTERED": If the token is unregistered.
            "SENDER_ID_MISMATCH": If the token belongs to a different sender ID.
            "INVALID_ARGUMENT": If the token or payload is invalid.
            "TRANSIENT_FAILURE": If transient delivery/network error.
            "FIREBASE_NOT_INITIALIZED": If Firebase was not configured/initialized.
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

        # Create pending delivery log (Phase 2 & Phase 8 tracking)
        log_record = PushDeliveryLog(
            notification_id=notification_id,
            user_id=user_id,
            device_token_id=device_token_id,
            push_provider="FCM",
            status="PENDING",
            notification_type=notification_type,
            platform=platform,
            created_at=datetime.utcnow()
        )
        db.add(log_record)
        try:
            db.commit()
            db.refresh(log_record)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create pending push delivery log: {e}")

        # Check if Firebase is configured/initialized to prevent cascade deactivations on missing credentials
        if not firebase_admin._apps:
            logger.error("Firebase Admin SDK is not initialized. Suppressing push and token invalidation.")
            if log_record.id:
                log_record.status = "FAILED"
                log_record.error_message = "Firebase SDK not initialized"
                try:
                    db.commit()
                except Exception:
                    db.rollback()
            return "FIREBASE_NOT_INITIALIZED"

        log_record.sent_at = datetime.utcnow()

        try:
            response = messaging.send(message)
            logger.info(f"[PUSH EVENT] push_sent | notification_id={notification_id} | user_id={user_id} | token_id={device_token_id} | type={notification_type}")
            
            # Update log (Phase 2 & Phase 8)
            log_record.status = "SENT"
            log_record.push_message_id = response
            db.commit()
            return "SUCCESS"
        except messaging.UnregisteredError as ue:
            logger.warning(f"[PUSH EVENT] token_deactivated | reason=unregistered | notification_id={notification_id} | user_id={user_id} | token_id={device_token_id} | Error: {ue}")
            log_record.status = "FAILED"
            log_record.error_message = f"UnregisteredError: {ue}"
            db.commit()
            return "UNREGISTERED"
        except SenderIdMismatchError as se:
            logger.warning(f"[PUSH EVENT] token_deactivated | reason=sender_id_mismatch | notification_id={notification_id} | user_id={user_id} | token_id={device_token_id} | Error: {se}")
            log_record.status = "FAILED"
            log_record.error_message = f"SenderIdMismatchError: {se}"
            db.commit()
            return "SENDER_ID_MISMATCH"
        except InvalidArgumentError as ie:
            logger.warning(f"[PUSH EVENT] token_deactivated | reason=invalid_argument | notification_id={notification_id} | user_id={user_id} | token_id={device_token_id} | Error: {ie}")
            log_record.status = "FAILED"
            log_record.error_message = f"InvalidArgumentError: {ie}"
            db.commit()
            return "INVALID_ARGUMENT"
        except Exception as e:
            logger.error(f"[PUSH EVENT] push_failed | reason=transient | notification_id={notification_id} | user_id={user_id} | token_id={device_token_id} | Error: {e}")
            log_record.status = "FAILED"
            log_record.error_message = str(e)
            db.commit()
            return "TRANSIENT_FAILURE"

    @staticmethod
    async def _send_and_process_token(
        db: Session,
        user_id: int,
        token_record: DeviceToken,
        title: str,
        body: str,
        notification_id: int,
        notification_type: Optional[str],
        metadata: Optional[Dict[str, Any]],
        now_utc: datetime
    ) -> bool:
        status = await PushNotificationService.send_push_notification(
            db=db,
            user_id=user_id,
            device_token_id=token_record.id,
            device_token=token_record.device_token,
            title=title,
            body=body,
            metadata=metadata,
            notification_id=notification_id,
            notification_type=notification_type,
            platform=token_record.platform
        )
        
        if status == "SUCCESS":
            token_record.last_push_success = now_utc
            token_record.failure_count = 0
            return True
        elif status in ("UNREGISTERED", "SENDER_ID_MISMATCH", "INVALID_ARGUMENT"):
            token_record.last_push_failure = now_utc
            token_record.failure_count += 1
            token_record.is_active = False
            logger.info(f"FCM token {token_record.device_token[:15]}... invalid ({status}), marked inactive.")
            return False
        elif status == "FIREBASE_NOT_INITIALIZED":
            logger.warning(f"Skipping token tracking update for {token_record.device_token[:15]}... because Firebase is not initialized.")
            return False
        else:  # TRANSIENT_FAILURE
            token_record.last_push_failure = now_utc
            token_record.failure_count += 1
            if token_record.failure_count >= 3:
                token_record.is_active = False
                logger.info(f"FCM token {token_record.device_token[:15]}... failed {token_record.failure_count} times, marked inactive.")
            
            # Queue for retry (Phase 4 / Phase 9 retry queue integration)
            try:
                retry_job = PushRetryQueue(
                    notification_id=notification_id,
                    device_token_id=token_record.id,
                    retry_count=0,
                    next_retry_at=datetime.now(timezone.utc) + timedelta(minutes=1),
                    status="PENDING"
                )
                db.add(retry_job)
                logger.info(f"[PUSH EVENT] push_queued | notification_id={notification_id} | user_id={user_id} | token_id={token_record.id} | type={notification_type}")
            except Exception as re:
                logger.error(f"Failed to queue push retry job: {re}")
            return False

    @staticmethod
    async def send_to_user(
        db: Session,
        user_id: int,
        title: str,
        body: str,
        notification_id: int,
        notification_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Retrieves all active device tokens for the user, sends push notifications,
        updates failure/success counts, and deactivates invalid/failing ones concurrently.
        Returns True if at least one push was successfully sent, False otherwise.
        """
        active_tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == True
        ).all()

        if not active_tokens:
            logger.debug(f"No active device tokens found for user {user_id}. Skipping push.")
            return False

        now_utc = datetime.now(timezone.utc)
        
        # Batch token processing (Phase 9 concurrent FCM sends)
        tasks = [
            PushNotificationService._send_and_process_token(
                db=db,
                user_id=user_id,
                token_record=token_record,
                title=title,
                body=body,
                notification_id=notification_id,
                notification_type=notification_type,
                metadata=metadata,
                now_utc=now_utc
            )
            for token_record in active_tokens
        ]
        
        results = await asyncio.gather(*tasks)
        any_success = any(results)

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
        notification_id: int,
        notification_type: Optional[str] = None,
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

        # Check if Firebase is initialized
        if not firebase_admin._apps:
            logger.error("Firebase Admin SDK is not initialized. Suppressing multicast push.")
            return

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

                    # Create pending delivery log
                    log_record = PushDeliveryLog(
                        notification_id=notification_id,
                        user_id=token_record.user_id,
                        device_token_id=token_record.id,
                        push_provider="FCM",
                        status="PENDING",
                        notification_type=notification_type,
                        platform=token_record.platform,
                        created_at=datetime.utcnow(),
                        sent_at=datetime.utcnow()
                    )
                    db.add(log_record)
                    
                    if resp.success:
                        token_record.last_push_success = now_utc
                        token_record.failure_count = 0
                        log_record.status = "SENT"
                        log_record.push_message_id = resp.message_id
                    else:
                        token_record.last_push_failure = now_utc
                        token_record.failure_count += 1
                        exception = resp.exception
                        
                        log_record.status = "FAILED"
                        log_record.error_message = str(exception)
                        
                        is_invalid_err = isinstance(exception, (messaging.UnregisteredError, SenderIdMismatchError, InvalidArgumentError))
                        if is_invalid_err or token_record.failure_count >= 3:
                            token_record.is_active = False
                            logger.info(f"Multicast FCM token {token[:15]}... invalid or failed too many times, marked inactive.")
                        else:
                            # Queue transient failure for retry
                            try:
                                retry_job = PushRetryQueue(
                                    notification_id=notification_id,
                                    device_token_id=token_record.id,
                                    retry_count=0,
                                    next_retry_at=datetime.now(timezone.utc) + timedelta(minutes=1),
                                    status="PENDING"
                                )
                                db.add(retry_job)
                                logger.info(f"[PUSH EVENT] push_queued | notification_id={notification_id} | user_id={token_record.user_id} | token_id={token_record.id} | type={notification_type}")
                            except Exception as re:
                                logger.error(f"Failed to queue push retry job in multicast: {re}")
                
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to commit multicast token tracking updates: {e}")
                    
        except Exception as e:
            logger.error(f"FCM multicast batch delivery failed: {e}")


# Global service instance
push_service = PushNotificationService()
