from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False)
    jti = Column(String, nullable=False, unique=True, index=True)  # JWT ID for tracking
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with User
    user = relationship("User", back_populates="refresh_tokens")

    def is_expired(self) -> bool:
        """Check if the refresh token has expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the refresh token is valid (not expired and not revoked)."""
        return not self.is_expired() and not self.is_revoked

    def update_last_used(self):
        """Update the last_used_at timestamp to current time."""
        self.last_used_at = datetime.utcnow()

    def revoke(self):
        """Revoke the refresh token."""
        self.is_revoked = True

    @classmethod
    def create_for_user(cls, user_id: int, token_hash: str, expires_in_days: int = 7):
        """Create a new refresh token for a user."""
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        return cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
