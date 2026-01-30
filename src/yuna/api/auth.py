"""
JWT Authentication for YUNA API.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET", "yuna-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    """JWT Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    username: Optional[str] = None
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class UserInfo(BaseModel):
    """User information response."""
    username: str
    is_authenticated: bool = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(username: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        username: The username to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)

    to_encode = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string

    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        exp = payload.get("exp")

        if username is None:
            return None

        return TokenData(
            username=username,
            exp=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
        )
    except JWTError:
        return None


def authenticate_user(username: str, password: str) -> Optional[str]:
    """
    Authenticate user with username and password.

    Args:
        username: The username
        password: The plain text password

    Returns:
        Username if authenticated, None otherwise
    """
    # Get credentials from environment
    valid_username = os.getenv("YUNA_USERNAME", "admin")
    valid_password = os.getenv("YUNA_PASSWORD")

    if not valid_password:
        # If no password set, use a default (should be changed in production)
        valid_password = "yuna"

    # Simple comparison (in production, use hashed passwords)
    if username == valid_username and password == valid_password:
        return username

    return None
