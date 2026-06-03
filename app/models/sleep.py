import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Date, Time,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class SleepSession(Base):
    __tablename__ = "sleep_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    sleep_score = Column(Integer, nullable=False)
    sleep_quality = Column(String(50), nullable=False)
    is_nap = Column(Boolean, default=False, nullable=False)
    session_source = Column(String(50), default="manual", nullable=False)
    timezone = Column(String(100), default="UTC", nullable=False)
    deep_sleep_minutes = Column(Integer, default=0, nullable=False)
    light_sleep_minutes = Column(Integer, default=0, nullable=False)
    rem_sleep_minutes = Column(Integer, default=0, nullable=False)
    awake_minutes = Column(Integer, default=0, nullable=False)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationship to User model
    user = relationship("User")

    # Table constraints and indexes
    __table_args__ = (
        Index("idx_sleep_user_start", "user_id", "start_time"),
        Index("idx_sleep_user_updated", "user_id", "updated_at"),
        Index("idx_sleep_deleted", "deleted_at"),
    )

    def __repr__(self):
        return f"<SleepSession(id={self.id}, user_id={self.user_id}, start_time={self.start_time}, duration_minutes={self.duration_minutes})>"


class UserDailySleep(Base):
    __tablename__ = "user_daily_sleep"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sleep_date = Column(Date, nullable=False, index=True)
    total_sleep_minutes = Column(Integer, default=0, nullable=False)
    total_sessions = Column(Integer, default=0, nullable=False)
    avg_sleep_score = Column(Float, default=0.0, nullable=False)
    total_deep_sleep = Column(Integer, default=0, nullable=False)
    total_rem_sleep = Column(Integer, default=0, nullable=False)
    total_light_sleep = Column(Integer, default=0, nullable=False)
    sleep_consistency_score = Column(Integer, default=100, nullable=False)
    bed_time_avg = Column(Time, nullable=True)  # Stored as Time of day
    wake_time_avg = Column(Time, nullable=True)  # Stored as Time of day
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to User model
    user = relationship("User")

    # Table constraints
    __table_args__ = (
        UniqueConstraint("user_id", "sleep_date", name="unique_user_sleep_date"),
    )

    def __repr__(self):
        return f"<UserDailySleep(user_id={self.user_id}, sleep_date={self.sleep_date}, total_sleep_minutes={self.total_sleep_minutes})>"


class UserMonthlySleep(Base):
    __tablename__ = "user_monthly_sleep"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    total_sleep_minutes = Column(Integer, default=0, nullable=False)
    avg_sleep_minutes = Column(Float, default=0.0, nullable=False)
    avg_sleep_score = Column(Float, default=0.0, nullable=False)
    total_sessions = Column(Integer, default=0, nullable=False)
    best_sleep_score = Column(Integer, default=0, nullable=False)
    worst_sleep_score = Column(Integer, default=0, nullable=False)
    avg_deep_sleep = Column(Float, default=0.0, nullable=False)
    avg_rem_sleep = Column(Float, default=0.0, nullable=False)
    sleep_consistency_score = Column(Float, default=100.0, nullable=False)
    days_tracked = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to User model
    user = relationship("User")

    # Table constraints
    __table_args__ = (
        UniqueConstraint("user_id", "year", "month", name="unique_user_sleep_year_month"),
    )

    def __repr__(self):
        return f"<UserMonthlySleep(user_id={self.user_id}, year={self.year}, month={self.month}, total_sleep_minutes={self.total_sleep_minutes})>"


class UserYearlySleep(Base):
    __tablename__ = "user_yearly_sleep"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    total_sleep_minutes = Column(Integer, default=0, nullable=False)
    avg_sleep_minutes = Column(Float, default=0.0, nullable=False)
    avg_sleep_score = Column(Float, default=0.0, nullable=False)
    total_sessions = Column(Integer, default=0, nullable=False)
    days_tracked = Column(Integer, default=0, nullable=False)
    best_month_score = Column(Float, default=0.0, nullable=False)
    worst_month_score = Column(Float, default=0.0, nullable=False)
    sleep_consistency_score = Column(Float, default=100.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to User model
    user = relationship("User")

    # Table constraints
    __table_args__ = (
        UniqueConstraint("user_id", "year", name="unique_user_sleep_year"),
    )

    def __repr__(self):
        return f"<UserYearlySleep(user_id={self.user_id}, year={self.year}, total_sleep_minutes={self.total_sleep_minutes})>"
