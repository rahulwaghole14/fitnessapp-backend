from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Admin(Base):
    """
    Admin model for system administration.
    Only one admin record is allowed in the database.
    """
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)  # Hashed password using bcrypt
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Admin(id={self.id}, email={self.email}, is_active={self.is_active})>"


class AdminRefreshToken(Base):
    """
    Admin refresh token model for JWT token management.
    """
    __tablename__ = "admin_refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    token_hash = Column(String, nullable=False)  # Hashed refresh token
    jti = Column(String, nullable=False, unique=True)  # JWT ID for tracking
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    admin = relationship("Admin")

    def is_expired(self):
        """Check if the refresh token has expired"""
        return datetime.utcnow() > self.expires_at

    def __repr__(self):
        return f"<AdminRefreshToken(id={self.id}, admin_id={self.admin_id}, jti={self.jti}, is_revoked={self.is_revoked})>"
