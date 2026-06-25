from uuid import UUID
from typing import Optional, Dict, Any, List
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.feedback import Feedback, FeedbackCategory, FeedbackStatus
from app.models.user import User


class FeedbackAdminSelector:

    @staticmethod
    def get_admin_feedback_list(
        db: Session,
        page: int = 1,
        limit: int = 20,
        category: Optional[FeedbackCategory] = None,
        rating: Optional[int] = None,
        status: Optional[FeedbackStatus] = None,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Paginated and filtered list of all feedbacks.
        """
        offset = (page - 1) * limit
        query = db.query(Feedback)

        # Apply filters
        if category:
            query = query.filter(Feedback.category == category)
        if rating is not None:
            query = query.filter(Feedback.rating == rating)
        if status:
            query = query.filter(Feedback.status == status)
        if search_query:
            query = query.filter(Feedback.message.ilike(f"%{search_query}%"))

        # Preload user details
        query = query.options(joinedload(Feedback.user))

        total = query.count()
        feedbacks = query.order_by(Feedback.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "feedbacks": feedbacks,
            "total": total,
            "page": page,
            "limit": limit
        }

    @staticmethod
    def compute_analytics(db: Session) -> Dict[str, Any]:
        """
        Calculate total feedback count, average rating, category/rating distributions,
        and status-wise counts.
        """
        total = db.query(Feedback).count()
        
        avg_rating_res = db.query(func.avg(Feedback.rating)).scalar()
        average_rating = round(float(avg_rating_res), 1) if avg_rating_res is not None else 0.0

        # Pending count (PENDING)
        pending = db.query(Feedback).filter(Feedback.status == FeedbackStatus.PENDING).count()

        # Resolved count (RESOLVED)
        resolved = db.query(Feedback).filter(Feedback.status == FeedbackStatus.RESOLVED).count()

        # Category distribution
        category_counts = db.query(Feedback.category, func.count(Feedback.id)).group_by(Feedback.category).all()
        cat_dist = {cat.value: 0 for cat in FeedbackCategory}
        for cat, count in category_counts:
            if cat:
                cat_dist[cat.value] = count

        # Rating distribution
        rating_counts = db.query(Feedback.rating, func.count(Feedback.id)).group_by(Feedback.rating).all()
        rating_dist = {str(i): 0 for i in range(1, 6)}
        for val, count in rating_counts:
            if val is not None and str(val) in rating_dist:
                rating_dist[str(val)] = count

        return {
            "total_feedbacks": total,
            "average_rating": average_rating,
            "category_distribution": cat_dist,
            "rating_distribution": rating_dist,
            "pending_count": pending,
            "resolved_count": resolved
        }

    @classmethod
    def get_analytics_cached(cls, db: Session) -> Dict[str, Any]:
        """
        Retrieve pre-computed analytics from the in-memory cache,
        falling back to a database query if the cache is empty.
        """
        from app.tasks import ANALYTICS_CACHE
        if ANALYTICS_CACHE["analytics"] is not None:
            return ANALYTICS_CACHE["analytics"]
        
        # Recalculate
        metrics = cls.compute_analytics(db)
        ANALYTICS_CACHE["analytics"] = metrics
        return metrics
