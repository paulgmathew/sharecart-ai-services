from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import Settings, get_settings
from app.models.auth_models import CurrentUser
from app.security.jwt_validator import JWTValidator


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_jwt_validator() -> JWTValidator:
    settings: Settings = get_settings()
    return JWTValidator(settings)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    validator: JWTValidator = Depends(get_jwt_validator),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    return validator.validate(token)
