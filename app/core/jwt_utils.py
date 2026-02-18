import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from jose import JWTError, jwt
import bcrypt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set")


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int) -> Tuple[str, str]:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())  # Generate unique JWT ID
    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh", "jti": jti}
    refresh_token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    token_hash = hash_refresh_token(refresh_token)
    return refresh_token, token_hash


def decode_access_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        if is_token_expired(payload):
            raise JWTError("Token expired")
        return payload
    except JWTError:
        raise JWTError("Invalid access token")


def decode_refresh_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        if is_token_expired(payload):
            raise JWTError("Token expired")
        return payload
    except JWTError:
        raise JWTError("Invalid refresh token")


def hash_refresh_token(refresh_token: str) -> str:
    salt = bcrypt.gensalt()
    # Truncate refresh token to 72 bytes for bcrypt compatibility
    refresh_token_bytes = refresh_token.encode('utf-8')[:72]
    hashed = bcrypt.hashpw(refresh_token_bytes, salt)
    return hashed.decode('utf-8')


def verify_refresh_token(refresh_token: str, stored_hash: str) -> bool:
    try:
        # Truncate refresh token to 72 bytes for bcrypt compatibility
        refresh_token_bytes = refresh_token.encode('utf-8')[:72]
        stored_hash_bytes = stored_hash.encode('utf-8')
        return bcrypt.checkpw(refresh_token_bytes, stored_hash_bytes)
    except:
        return False


def is_token_expired(payload: Dict) -> bool:
    exp = payload.get("exp")
    if not exp:
        return True
    return datetime.utcnow() > datetime.fromtimestamp(exp)
