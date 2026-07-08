from fastapi import APIRouter, Header, HTTPException
import os
import logging
from typing import Optional
from app.services.cron_notification_processor import process_pending_notifications

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/internal/process-notifications")
async def process_notifications(
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")
):
    """
    Cron-Job.org endpoint to process all due scheduled notifications.
    Protected by X-Internal-Key header validation.
    """
    internal_secret = os.getenv("INTERNAL_SECRET_KEY")
    if not internal_secret:
        logger.error("[CRON] INTERNAL_SECRET_KEY is not configured in the environment.")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: INTERNAL_SECRET_KEY not configured"
        )

    if not x_internal_key or x_internal_key != internal_secret:
        logger.warning("[CRON] Unauthorized request rejected: Invalid or missing X-Internal-Key.")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid credentials"
        )

    try:
        jobs_processed = await process_pending_notifications()
        return {"status": "success", "jobs_processed": jobs_processed}
    except Exception as e:
        logger.exception(f"[CRON] Unexpected error occurred during processing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )

