from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class DailyActivity(Base):
    __tablename__ = "daily_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    steps = Column(Integer, default=0)
    distance_km = Column(Float, default=0.0)
    calories = Column(Float, default=0.0)
    active_minutes = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with User model
    user = relationship("User", back_populates="daily_activities")

    # Ensure unique constraint: one record per user per day
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='unique_user_date'),
    )

    def __repr__(self):
        return f"<DailyActivity(user_id={self.user_id}, date={self.date}, steps={self.steps})>"
