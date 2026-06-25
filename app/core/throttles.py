from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user_id
from app.models.feedback import Feedback

def feedback_rate_limiter(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Dependency to throttle feedback submission rates.
    Enforces a hard limit of maximum 5 feedback submissions per user per hour.
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # Query database to count the user's submissions in the last hour
    recent_submissions_count = db.query(Feedback).filter(
        Feedback.user_id == user_id,
        Feedback.created_at >= one_hour_ago
    ).count()

    if recent_submissions_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 feedback submissions per user per hour."
        )
