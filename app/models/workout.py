from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from datetime import datetime
from app.core.database import Base

class Workout(Base):
    __tablename__ = "workouts"
    __table_args__ = (
        UniqueConstraint('title', 'activity_level', name='unique_workout'),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    workout_image_url = Column(String, nullable=False)
    workout_video_url = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    calorie_burn = Column(Integer, nullable=False)
    activity_level = Column(String, nullable=False)
    workout_category = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Workout(id={self.id}, title={self.title}, activity_level={self.activity_level})>"
