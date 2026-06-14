from __future__ import annotations

from fastapi import HTTPException, status
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
import structlog

from app.config.settings import Settings
from app.models.auth_models import CurrentUser


logger = structlog.get_logger(__name__)


class JWTValidator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(self, token: str) -> CurrentUser:
        header_alg = None
        claim_keys: list[str] = []
        try:
            header = jwt.get_unverified_header(token)
            header_alg = header.get("alg")
        except Exception:
            logger.warning("jwt_unverified_header_parse_failed")

        try:
            unverified_claims = jwt.decode(token, options={"verify_signature": False})
            claim_keys = sorted(list(unverified_claims.keys()))
        except Exception:
            logger.warning("jwt_unverified_claims_parse_failed")

        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
                options={"require": ["sub", "exp"]},
            )
        except ExpiredSignatureError as exc:
            logger.warning(
                "jwt_validation_expired",
                expected_algorithm=self._settings.jwt_algorithm,
                token_header_algorithm=header_alg,
                token_claim_keys=claim_keys,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            ) from exc
        except InvalidTokenError as exc:
            logger.warning(
                "jwt_validation_invalid",
                expected_algorithm=self._settings.jwt_algorithm,
                token_header_algorithm=header_alg,
                token_claim_keys=claim_keys,
                jwt_error_type=type(exc).__name__,
                jwt_error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from exc

        user_id = payload.get("sub")
        email = payload.get("email")
        exp = payload.get("exp")

        if not user_id or not exp:
            logger.warning(
                "jwt_validation_claims_invalid",
                token_claim_keys=sorted(list(payload.keys())),
                has_user_id=bool(user_id),
                has_exp=bool(exp),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
            )

        logger.info(
            "jwt_validation_succeeded",
            user_id=str(user_id),
            token_claim_keys=sorted(list(payload.keys())),
        )

        email_value = str(email) if email is not None else None
        return CurrentUser(user_id=str(user_id), email=email_value, exp=int(exp))
