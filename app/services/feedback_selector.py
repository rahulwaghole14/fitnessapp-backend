from uuid import UUID
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.models.feedback import Feedback


class FeedbackSelector:

    @staticmethod
    def get_user_feedback_history(
        db: Session,
        user_id: int
    ) -> List[Feedback]:
        """
        Retrieve all feedback submitted by the authenticated user, ordered by latest.
        """
        return db.query(Feedback).filter(
            Feedback.user_id == user_id
        ).options(
            joinedload(Feedback.user)
        ).order_by(Feedback.created_at.desc()).all()

    @staticmethod
    def get_feedback_details(
        db: Session,
        feedback_id: UUID
    ) -> Optional[Feedback]:
        """
        Fetch full details of a specific feedback submission.
        """
        return db.query(Feedback).filter(
            Feedback.id == feedback_id
        ).options(
            joinedload(Feedback.user)
        ).first()
