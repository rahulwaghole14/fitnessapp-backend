import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

def generate_otp() -> str:
    """
    Generates a cryptographically secure 6-digit OTP.
    secrets.randbelow(900000) generates numbers from 0 to 899999.
    Adding 100000 ensures it is always exactly 6 digits (100000 to 999999).
    """
    return str(secrets.randbelow(900000) + 100000)

def check_otp_lock(entity):
    """
    Checks if the user/admin OTP is currently locked.
    Raises HTTP 429 Too Many Requests if locked.
    Resets the lock and attempts counter if the lock duration has expired.
    """
    if entity.otp_locked_until:
        # Comparison uses timezone-naive UTC datetime to match db columns
        now = datetime.utcnow()
        if now < entity.otp_locked_until:
            remaining_seconds = int((entity.otp_locked_until - now).total_seconds())
            remaining_minutes = max(1, remaining_seconds // 60)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed attempts. Account is locked. Please try again after {remaining_minutes} minutes."
            )
        else:
            # Lock has expired, reset attempts and lock
            entity.otp_attempts = 0
            entity.otp_locked_until = None

def handle_failed_otp_attempt(db: Session, entity):
    """
    Increments the failed OTP attempts counter.
    Locks the entity if the attempts reach the threshold of 5.
    """
    entity.otp_attempts += 1
    if entity.otp_attempts >= 5:
        entity.otp_locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Account is locked. Please try again after 15 minutes."
        )
    db.commit()

def handle_successful_otp_verification(db: Session, entity, clear_otp: bool = False):
    """
    Resets the attempts counter and lock on successful verification.
    Optionally clears the OTP and otp_created_at fields.
    """
    entity.otp_attempts = 0
    entity.otp_locked_until = None
    if clear_otp:
        entity.otp = None
        entity.otp_created_at = None
    db.commit()
