from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.jwt_utils import create_access_token, create_refresh_token, decode_refresh_token, verify_refresh_token
from app.core.auth_dependencies import get_current_user
from app.models.user import User
from app.models.refresh_token import RefreshToken


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> RefreshTokenResponse:
    """Refresh access token using refresh token with JTI-based token rotation."""
    try:
        # Decode and validate the refresh token
        payload = decode_refresh_token(request.refresh_token)
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        
        # Find the specific refresh token in database using JTI
        db_token = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.jti == jti,  # Match specific JWT ID
            RefreshToken.is_revoked == False
        ).first()
        
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Verify the token hash
        if not verify_refresh_token(request.refresh_token, db_token.token_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if token is still valid
        if not db_token.is_valid():
            # Revoke token if it's expired
            db_token.revoke()
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Rotate refresh token using JTI tracking (prevents old token reuse)
        new_access_token = create_access_token(user_id)
        new_refresh_token, new_refresh_token_hash = create_refresh_token(user_id)
        
        # Extract JTI from new refresh token
        new_payload = decode_refresh_token(new_refresh_token)
        new_jti = new_payload.get("jti")
        
        # Update existing refresh token record with new token info
        db_token.token_hash = new_refresh_token_hash
        db_token.jti = new_jti  # Update to new JTI
        db_token.expires_at = datetime.utcnow() + timedelta(days=7)
        db_token.last_used_at = datetime.utcnow()
        db.commit()
        
        return RefreshTokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


def logout(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Dict:
    """Logout by revoking a specific refresh token."""
    try:
        # Decode and validate the refresh token
        payload = decode_refresh_token(request.refresh_token)
        user_id = int(payload.get("sub"))
        
        # Find and revoke the specific refresh token
        db_tokens = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).all()
        
        revoked_count = 0
        for db_token in db_tokens:
            if verify_refresh_token(request.refresh_token, db_token.token_hash):
                db_token.revoke()
                revoked_count += 1
                break
        
        if revoked_count == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        db.commit()
        return {"message": "Logout successful"}
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Logout by revoking all refresh tokens for the current user."""
    try:
        # Revoke all refresh tokens for the user
        db_tokens = db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_revoked == False
        ).all()
        
        for token in db_tokens:
            token.revoke()
        
        db.commit()
        return {"message": "Logged out from all devices successfully"}
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout from all devices"
        )
