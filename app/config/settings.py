from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Literal, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    app_name: str = "sharecart-ai-service"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    jwt_secret: str = Field(default="change-me", min_length=8)
    jwt_algorithm: str = "HS256"

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 25.0

    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_extensions: tuple[str, ...] = ("jpg", "jpeg", "png", "webp")
    max_image_dimension: int = 2200

    rate_limit_hourly: int = 10
    rate_limit_daily: int = 50

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            values = [item.strip() for item in value.split(",") if item.strip()]
            return values or ["*"]
        return ["*"]

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            app_name=os.getenv("APP_NAME", "sharecart-ai-service"),
            environment=os.getenv("APP_ENV", "local"),
            api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            jwt_secret=os.getenv("JWT_SECRET", "change-me"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "25")),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
            max_image_dimension=int(os.getenv("MAX_IMAGE_DIMENSION", "2200")),
            rate_limit_hourly=int(os.getenv("RATE_LIMIT_HOURLY", "10")),
            rate_limit_daily=int(os.getenv("RATE_LIMIT_DAILY", "50")),
            cors_origins=os.getenv("CORS_ORIGINS", "*"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
