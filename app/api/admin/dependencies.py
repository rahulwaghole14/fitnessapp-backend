from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

from app.core.database import get_db
from app.models.admin import Admin

# Load environment variables
load_dotenv()

# JWT Configuration
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")
ALGORITHM = "HS256"

# HTTP Bearer scheme for token extraction
security = HTTPBearer()


async def get_current_admin(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> Admin:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the JWT token
        payload = jwt.decode(
            credentials.credentials,
            ADMIN_SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        # Extract admin_id from token
        admin_id: int = payload.get("admin_id")

        if admin_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Get admin from database
    admin = db.query(Admin).filter(Admin.id == admin_id).first()

    if admin is None:
        raise credentials_exception

    # Check if admin is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return admin


async def get_current_active_admin(
        current_admin: Admin = Depends(get_current_admin)
) -> Admin:

    if not current_admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is deactivated"
        )
    return current_admin
