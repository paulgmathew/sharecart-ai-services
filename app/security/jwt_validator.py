from __future__ import annotations

from fastapi import HTTPException, status
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config.settings import Settings
from app.models.auth_models import CurrentUser


class JWTValidator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(self, token: str) -> CurrentUser:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
                options={"require": ["exp"]},
            )
        except ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            ) from exc
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from exc

        user_id = payload.get("userId") or payload.get("user_id") or payload.get("sub")
        email = payload.get("email")
        exp = payload.get("exp")

        if not user_id or not email or not exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
            )

        return CurrentUser(user_id=str(user_id), email=str(email), exp=int(exp))
