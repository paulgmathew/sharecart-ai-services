from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import structlog
from starlette.requests import Request

from app.config.settings import Settings, get_settings
from app.models.auth_models import CurrentUser
from app.security.jwt_validator import JWTValidator


bearer_scheme = HTTPBearer(auto_error=False)
logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def get_jwt_validator() -> JWTValidator:
    settings: Settings = get_settings()
    return JWTValidator(settings)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    validator: JWTValidator = Depends(get_jwt_validator),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        logger.warning(
            "auth_failed_missing_bearer_token",
            path=request.url.path,
            method=request.method,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = credentials.credentials.strip()
    if not token:
        logger.warning(
            "auth_failed_empty_bearer_token",
            path=request.url.path,
            method=request.method,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    user = validator.validate(token)
    structlog.contextvars.bind_contextvars(user_id=user.user_id)
    logger.info(
        "auth_succeeded",
        path=request.url.path,
        method=request.method,
        user_id=user.user_id,
    )
    return user
