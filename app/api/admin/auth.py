from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv
import bcrypt
from jose import jwt, JWTError
import hashlib

from app.models.admin import Admin, AdminRefreshToken
from app.core.database import get_db
from .schemas import AdminRegister, AdminLogin, AdminResponse, TokenResponse

# Load environment variables
load_dotenv()

# JWT Configuration
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")
if not ADMIN_SECRET_KEY:
    raise ValueError("ADMIN_SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using bcrypt.
    """
    # Truncate password to 72 bytes (bcrypt limit)
    password_bytes = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    Truncates password to 72 bytes as required by bcrypt.
    """
    # Truncate password to 72 bytes (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, ADMIN_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(admin_id: int) -> tuple[str, str]:
    """
    Create a JWT refresh token and return both token and its hash.

    Args:
        admin_id: Admin ID to include in token

    Returns:
        Tuple of (refresh_token, token_hash)
    """
    # Create JWT ID for tracking
    jti = str(admin_id) + "_" + str(int(datetime.utcnow().timestamp()))

    # Create refresh token with longer expiry
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "admin_id": admin_id,
        "jti": jti,
        "exp": expire,
        "type": "refresh"
    }

    refresh_token = jwt.encode(to_encode, ADMIN_SECRET_KEY, algorithm=ALGORITHM)

    # Create hash of the token for secure storage
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    return refresh_token, token_hash


def verify_refresh_token(refresh_token: str, token_hash: str) -> bool:
    """
    Verify that a refresh token matches the stored hash.

    Args:
        refresh_token: The refresh token to verify
        token_hash: The stored hash to compare against

    Returns:
        True if token matches hash, False otherwise
    """
    computed_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    return computed_hash == token_hash


def decode_refresh_token(refresh_token: str) -> dict:
    """
    Decode and validate a refresh token.

    Args:
        refresh_token: The refresh token to decode

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(refresh_token, ADMIN_SECRET_KEY, algorithms=[ALGORITHM])

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # Verify required fields
        admin_id = payload.get("admin_id")
        jti = payload.get("jti")

        if not admin_id or not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure"
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


async def register_admin(
        admin_data: AdminRegister,
        db: Session = Depends(get_db)
) -> AdminResponse:
    """
    Register a new admin. Only one admin is allowed in the system.
    """
    # Check if any admin already exists
    existing_admin = db.query(Admin).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin already exists. Only one admin is allowed in the system."
        )

    # Check if email is already registered (though this should be caught by the unique constraint)
    email_exists = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password
    hashed_password = get_password_hash(admin_data.password)

    # Create new admin
    new_admin = Admin(
        username=admin_data.username,
        email=admin_data.email,
        password_hash=hashed_password,
        is_active=True
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return AdminResponse(
        id=new_admin.id,
        username=new_admin.username,
        email=new_admin.email,
        is_active=new_admin.is_active,
        created_at=new_admin.created_at
    )


async def login_admin(
        admin_data: AdminLogin,
        db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate admin and return JWT tokens (access + refresh).
    """
    # Find admin by email
    admin = db.query(Admin).filter(Admin.email == admin_data.email).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(admin_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if admin is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clean up any revoked refresh tokens for this admin before login
    db.query(AdminRefreshToken).filter(
        AdminRefreshToken.admin_id == admin.id,
        AdminRefreshToken.is_revoked == True
    ).delete()
    db.commit()

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"admin_id": admin.id}, expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token, token_hash = create_refresh_token(admin_id=admin.id)

    # Decode refresh token to get JTI
    payload = decode_refresh_token(refresh_token)
    jti = payload.get("jti")

    # Store refresh token in database
    db_refresh_token = AdminRefreshToken(
        admin_id=admin.id,
        token_hash=token_hash,
        jti=jti,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        last_used_at=datetime.utcnow()
    )
    db.add(db_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )
