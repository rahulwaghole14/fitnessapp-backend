from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    otp = Column(String, nullable=True)
    otp_created_at = Column(DateTime, nullable=True)  # Track OTP creation time for expiration
    is_verified = Column(Boolean, default=False)
    gender = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    weight_goal = Column(Float, nullable=True)
    activity_level = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)

    # Relationship with DailyActivity
    daily_activities = relationship("DailyActivity", back_populates="user")

    # Relationship with UserMonthlyActivity
    monthly_activities = relationship("UserMonthlyActivity", back_populates="user")

    # Relationship with UserYearlyActivity
    yearly_activities = relationship("UserYearlyActivity", back_populates="user")


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


class UserMonthlyActivity(Base):
    __tablename__ = "user_monthly_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)  # 1-12
    total_steps = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    total_calories = Column(Float, default=0.0)
    total_active_minutes = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with User model
    user = relationship("User", back_populates="monthly_activities")

    # Ensure unique constraint: one record per user per month
    __table_args__ = (
        UniqueConstraint('user_id', 'year', 'month', name='unique_user_year_month'),
    )

    def __repr__(self):
        return f"<UserMonthlyActivity(user_id={self.user_id}, year={self.year}, month={self.month}, steps={self.total_steps})>"


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
