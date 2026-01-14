from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
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

