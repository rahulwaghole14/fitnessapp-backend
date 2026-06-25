from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user_id
from app.api.admin.dependencies import get_current_admin
from app.models.feedback import Feedback
from app.models.admin import Admin

def verify_feedback_ownership(
    feedback_id: UUID,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Feedback:
    """
    Dependency to verify that the requesting user owns the feedback submission.
    Raises 404 if not found, and 403 if user is not the owner.
    """
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id
    ).first()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    if feedback.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this feedback."
        )

    return feedback


def verify_admin_user(
    admin: Admin = Depends(get_current_admin)
) -> Admin:
    """
    Dependency to enforce admin-only access.
    Delegates to existing get_current_admin dependency.
    """
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    return admin
