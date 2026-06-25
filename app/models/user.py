from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    otp = Column(String, nullable=True)
    otp_created_at = Column(DateTime, nullable=True)  # Track OTP creation time for expiration
    otp_attempts = Column(Integer, default=0, nullable=False)
    otp_locked_until = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)
    gender = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    weight_goal = Column(Float, nullable=True)
    activity_level = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    timezone = Column(String(100), default="Asia/Kolkata", nullable=False)
    sleep_goal = Column(Integer, default=480, nullable=False)
    last_websocket_seen = Column(DateTime(timezone=True), nullable=True)
    last_app_activity = Column(DateTime(timezone=True), nullable=True)

    # Relationship with DailyActivity
    daily_activities = relationship("DailyActivity", back_populates="user")

    # Relationship with UserMonthlyActivity
    monthly_activities = relationship("UserMonthlyActivity", back_populates="user")

    # Relationship with UserYearlyActivity
    yearly_activities = relationship("UserYearlyActivity", back_populates="user")

    # Relationship with RefreshToken
    refresh_tokens = relationship("RefreshToken", back_populates="user")

    # Relationship with DeviceToken
    device_tokens = relationship("DeviceToken", back_populates="user", cascade="all, delete-orphan")

    # Relationship with NotificationPreference
    notification_preference = relationship("NotificationPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

