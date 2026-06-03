import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PushNotificationService:
    @staticmethod
    async def send_push_notification(
        user_id: int,
        title: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Placeholder stub interface for future Firebase Cloud Messaging (FCM) or APNs integration.
        Currently logs push requests to output and behaves as a success trigger.
        """
        logger.info(
            f"[PUSH STUB] Queued push notification for User {user_id}: "
            f"'{title}' - message: '{body}' | metadata: {metadata}"
        )
        return True


# Global service instance
push_service = PushNotificationService()
