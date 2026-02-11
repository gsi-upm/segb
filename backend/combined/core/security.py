"""Authentication and authorization helpers."""

from __future__ import annotations

import os
from enum import Enum
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


class Role(str, Enum):
    AUDITOR = "auditor"
    LOGGER = "logger"
    ADMIN = "admin"


class User(BaseModel):
    username: str
    name: str | None = None
    roles: list[str]
    exp: int | None = None


SECRET_KEY = os.getenv("SECRET_KEY") or None
ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)


async def validate_token(
    auth_credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    """Validates JWT token when security is enabled, otherwise grants full local access."""
    if not SECRET_KEY:
        return User(
            username="anonymous_user",
            name="Unknown User - No Security Enabled",
            roles=[role.value for role in Role],
            exp=None,
        )

    if auth_credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded = jwt.decode(auth_credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return User(**decoded)
    except jwt.ExpiredSignatureError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Expired Token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Invalid Token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def require_roles(user: User, *, allowed: tuple[Role, ...]) -> None:
    """Checks that the user contains at least one allowed role."""
    allowed_values = {role.value for role in allowed}
    if not any(role in allowed_values for role in user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have permission to perform this action",
        )
