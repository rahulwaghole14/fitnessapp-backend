from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class UserYearlyActivity(Base):
    __tablename__ = "user_yearly_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    total_steps = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    total_calories = Column(Float, default=0.0)
    total_active_minutes = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with User model
    user = relationship("User", back_populates="yearly_activities")

    # Ensure unique constraint: one record per user per year
    __table_args__ = (
        UniqueConstraint('user_id', 'year', name='unique_user_year'),
    )

    def __repr__(self):
        return f"<UserYearlyActivity(user_id={self.user_id}, year={self.year}, steps={self.total_steps})>"
