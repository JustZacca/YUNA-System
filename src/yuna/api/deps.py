"""
FastAPI Dependencies for YUNA API.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from yuna.api.auth import decode_token, TokenData, UserInfo
from yuna.data.database import Database

# Security scheme
security = HTTPBearer(auto_error=False)

# Database singleton
_db: Optional[Database] = None


def get_db() -> Database:
    """
    Get database instance (singleton).

    Returns:
        Database instance
    """
    global _db
    if _db is None:
        _db = Database()
    return _db


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
) -> UserInfo:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        UserInfo for the authenticated user

    Raises:
        HTTPException: If not authenticated or token invalid
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_token(credentials.credentials)

    if token_data is None or token_data.username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInfo(username=token_data.username)


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
) -> Optional[UserInfo]:
    """
    Get the current user if authenticated, None otherwise.
    Does not raise exception for unauthenticated requests.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        UserInfo if authenticated, None otherwise
    """
    if credentials is None:
        return None

    token_data = decode_token(credentials.credentials)

    if token_data is None or token_data.username is None:
        return None

    return UserInfo(username=token_data.username)


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
OptionalUser = Annotated[Optional[UserInfo], Depends(get_optional_user)]
DbDep = Annotated[Database, Depends(get_db)]
