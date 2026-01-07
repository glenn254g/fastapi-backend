# backend/app/core/security.py
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        password_bytes = plain_password.encode("utf-8")
        # Truncate to 72 bytes for bcrypt
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        hashed_bytes = hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    # Convert password to bytes
    password_bytes = password.encode("utf-8")
    # Bcrypt has 72 byte limit, truncate if needed
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string
    return hashed.decode("utf-8")
