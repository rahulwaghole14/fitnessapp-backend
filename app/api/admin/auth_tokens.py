
#Admin JWT Token Management APIs - Refresh and Logout endpoints

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.admin import Admin, AdminRefreshToken
from .auth import decode_refresh_token, create_access_token, create_refresh_token, verify_refresh_token


class AdminRefreshTokenRequest(BaseModel):
    """Request schema for admin token refresh"""
    refresh_token: str


class AdminRefreshTokenResponse(BaseModel):
    """Response schema for admin token refresh"""
    access_token: str
    refresh_token: str  # Optional: new refresh token if rotation is enabled
    token_type: str = "bearer"


class AdminLogoutRequest(BaseModel):
    """Request schema for admin logout"""
    refresh_token: str


def refresh_admin_access_token(
        request: AdminRefreshTokenRequest,
        db: Session = Depends(get_db)
):

    refresh_token_str = request.refresh_token

    # Decode and validate refresh token structure
    try:
        payload = decode_refresh_token(refresh_token_str)
        admin_id = payload.get("admin_id")
        jti = payload.get("jti")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token format"
        )

    # Find the specific refresh token in database using JTI
    db_refresh_token = db.query(AdminRefreshToken).filter(
        AdminRefreshToken.admin_id == admin_id,
        AdminRefreshToken.jti == jti,
        AdminRefreshToken.is_revoked == False
    ).first()

    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked"
        )

    # Verify the refresh token hash matches stored hash
    if not verify_refresh_token(refresh_token_str, db_refresh_token.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check if refresh token has expired
    if db_refresh_token.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    try:
        # STEP 1: Generate new access token
        new_access_token = create_access_token(data={"admin_id": admin_id})

        # STEP 2: Generate new refresh token
        new_refresh_token, new_token_hash = create_refresh_token(admin_id=admin_id)

        # STEP 3: Extract JTI from new refresh token
        new_payload = decode_refresh_token(new_refresh_token)
        new_jti = new_payload.get("jti")

        # STEP 4: Update the existing refresh token record (like user system)
        db_refresh_token.token_hash = new_token_hash
        db_refresh_token.jti = new_jti  # Update to new JTI
        db_refresh_token.expires_at = datetime.utcnow() + timedelta(days=7)
        db_refresh_token.last_used_at = datetime.utcnow()

        # STEP 5: Commit changes
        db.commit()

        return AdminRefreshTokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )

    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


def logout_admin(
        request: AdminLogoutRequest,
        db: Session = Depends(get_db)
):

    refresh_token_str = request.refresh_token

    # Decode and validate refresh token structure
    try:
        payload = decode_refresh_token(refresh_token_str)
        admin_id = payload.get("admin_id")
        jti = payload.get("jti")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Find the specific refresh token in database using JTI
    db_refresh_token = db.query(AdminRefreshToken).filter(
        AdminRefreshToken.admin_id == admin_id,
        AdminRefreshToken.jti == jti
    ).first()

    # Strict validation: Return 401 if token not found
    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )

    # Strict validation: Return 401 if token already revoked
    if db_refresh_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already revoked"
        )

    # Strict validation: Return 401 if token expired
    if db_refresh_token.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    # Verify the token hash before revoking (extra security)
    if not verify_refresh_token(refresh_token_str, db_refresh_token.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    try:
        # Revoke the refresh token
        db_refresh_token.is_revoked = True
        db.commit()

        return {"message": "Logout successful"}

    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
