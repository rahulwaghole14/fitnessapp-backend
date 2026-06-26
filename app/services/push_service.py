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
    def send_fcm_network(
        device_token: str,
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends push notification using Firebase and returns result details.
        No database interactions.
        """
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

        if not firebase_admin._apps:
            return {"status": "FIREBASE_NOT_INITIALIZED", "error": "Firebase SDK not initialized"}

        try:
            response = messaging.send(message)
            return {"status": "SUCCESS", "message_id": response}
        except messaging.UnregisteredError as ue:
            return {"status": "UNREGISTERED", "error": str(ue)}
        except SenderIdMismatchError as se:
            return {"status": "SENDER_ID_MISMATCH", "error": str(se)}
        except InvalidArgumentError as ie:
            return {"status": "INVALID_ARGUMENT", "error": str(ie)}
        except Exception as e:
            return {"status": "TRANSIENT_FAILURE", "error": str(e)}

    @staticmethod
    def record_fcm_results_batch(
        db: Session,
        user_id: int,
        notification_id: int,
        notification_type: Optional[str],
        results: List[dict]
    ) -> bool:
        """
        Records batch FCM delivery logs, token status updates, and retry queue tasks in a single commit.
        """
        any_success = False
        now_utc = datetime.now(timezone.utc)
        
        token_ids = [r["token_record_id"] for r in results]
        tokens = db.query(DeviceToken).filter(DeviceToken.id.in_(token_ids)).all()
        token_map = {t.id: t for t in tokens}
        
        for r in results:
            token_record = token_map.get(r["token_record_id"])
            status = r["status"]
            
            # Create log record
            log_record = PushDeliveryLog(
                notification_id=notification_id,
                user_id=user_id,
                device_token_id=r["token_record_id"],
                push_provider="FCM",
                status="SENT" if status == "SUCCESS" else "FAILED",
                error_message=r.get("error"),
                push_message_id=r.get("message_id"),
                notification_type=notification_type,
                platform=r.get("platform"),
                created_at=now_utc,
                sent_at=now_utc if status == "SUCCESS" else None
            )
            db.add(log_record)
            
            if not token_record:
                continue
                
            if status == "SUCCESS":
                token_record.last_push_success = now_utc
                token_record.failure_count = 0
                any_success = True
            elif status in ("UNREGISTERED", "SENDER_ID_MISMATCH", "INVALID_ARGUMENT"):
                token_record.last_push_failure = now_utc
                token_record.failure_count += 1
                token_record.is_active = False
                logger.info(f"FCM token {token_record.device_token[:15]}... invalid ({status}), marked inactive.")
            elif status == "FIREBASE_NOT_INITIALIZED":
                pass
            else:  # TRANSIENT_FAILURE
                token_record.last_push_failure = now_utc
                token_record.failure_count += 1
                if token_record.failure_count >= 3:
                    token_record.is_active = False
                    logger.info(f"FCM token {token_record.device_token[:15]}... failed {token_record.failure_count} times, marked inactive.")
                
                # Queue retry
                try:
                    retry_job = PushRetryQueue(
                        notification_id=notification_id,
                        device_token_id=token_record.id,
                        retry_count=0,
                        next_retry_at=now_utc + timedelta(minutes=1),
                        status="PENDING"
                    )
                    db.add(retry_job)
                except Exception as re:
                    logger.error(f"Failed to queue push retry job: {re}")
                
        return any_success

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
        Backward compatible version that routes sends through network function and records results in a single commit.
        """
        active_tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == True
        ).all()

        if not active_tokens:
            return False

        results = []
        for token_record in active_tokens:
            res = PushNotificationService.send_fcm_network(
                device_token=token_record.device_token,
                title=title,
                body=body,
                metadata=metadata
            )
            res.update({
                "token_record_id": token_record.id,
                "platform": token_record.platform
            })
            results.append(res)
            
        any_success = PushNotificationService.record_fcm_results_batch(
            db=db,
            user_id=user_id,
            notification_id=notification_id,
            notification_type=notification_type,
            results=results
        )
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit token tracking updates for user {user_id}: {e}")
            any_success = False

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
