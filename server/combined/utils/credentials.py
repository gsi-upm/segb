from enum import Enum
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
import logging
import os

from pydantic import BaseModel

logger = logging.getLogger("segb.server.utils.credentials")

logger.info("Loading utils.credentials for SEGB server...")

SECRET_KEY = os.getenv("SECRET_KEY", '') or None

ALGORITHM = "HS256"

security = HTTPBearer()
### TOKEN VALIDATION FUNCTIONS ###

class Role(Enum):
    AUDITOR = "auditor"
    LOGGER = "logger"
    ADMIN = "admin"
    
class User(BaseModel):
    username: str
    name: str | None = None
    roles: list[str]
    exp: int | None = None

async def validate_token(auth_credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> dict:
    '''
        Validate the token for all endpoints.
        If the token is valid, return the decoded token data.
        If the token is invalid, return a 401 Unauthorized error.
        If the token is expired, return a 401 Unauthorized error.
        If no secret key is configured, return a default user object.
        In this case, security is disabled, and full access is granted ignoring the token.
        '''
    logger.debug("Validating token...")
    if not SECRET_KEY:
        logger.warning(
            "SECRET_KEY is not set. No security is enabled, and all endpoints are accessible without token validation.")
        # If the secret is None, we assume no security is enabled
        return User(
            username="anonymous_user",
            name="Unknown User - No Security Enabled",
            roles= [role for role in Role],
            exp=None
        )
    try:
        logger.debug("Decoding token...")
        token = auth_credentials.credentials
        decode = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info("Token validated successfully")
        logger.debug(f"Decoded token data: {decode}")
        return User(**decode)
    except jwt.ExpiredSignatureError as e:
        logger.debug(f"Expired Token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Expired Token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid Token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Invalid Token",
            headers={"WWW-Authenticate": "Bearer"}
        )

### END OF TOKEN VALIDATION FUNCTIONS ###