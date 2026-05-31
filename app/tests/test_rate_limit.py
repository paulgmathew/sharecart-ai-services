from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import io

from fastapi.testclient import TestClient
import jwt
from PIL import Image

from app.config.settings import get_settings
from app.main import app
from app.middleware.rate_limit import get_rate_limiter
from app.models.request_models import ScanType
from app.models.response_models import ExtractionItem, ExtractionSuccessResponse
from app.services.extraction_service import get_extraction_service


class FakeExtractionService:
    async def extract_items(self, image_bytes: bytes, scan_type: ScanType):
        del image_bytes
        return ExtractionSuccessResponse(
            storeName="Store",
            confidence=0.9,
            scanType=scan_type,
            items=[ExtractionItem(name="Eggs", price=3.99, quantity="1", unit="dozen", confidence=0.95)],
        )


def create_png_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "userId": user_id,
        "email": f"{user_id}@test.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_rate_limit_exceeded_returns_429() -> None:
    app.dependency_overrides[get_extraction_service] = lambda: FakeExtractionService()
    client = TestClient(app)

    limiter = get_rate_limiter()
    asyncio.run(limiter.reset())
    limiter.set_limits(hourly_limit=2, daily_limit=3)

    token = create_token("rl-user")

    for _ in range(2):
        response = client.post(
            "/api/v1/receipt/extract",
            headers={"Authorization": f"Bearer {token}"},
            data={"scanType": "RECEIPT"},
            files={"image": ("receipt.png", create_png_bytes(), "image/png")},
        )
        assert response.status_code == 200

    third = client.post(
        "/api/v1/receipt/extract",
        headers={"Authorization": f"Bearer {token}"},
        data={"scanType": "RECEIPT"},
        files={"image": ("receipt.png", create_png_bytes(), "image/png")},
    )

    assert third.status_code == 429
    assert third.json()["success"] is False

    limiter.set_limits(hourly_limit=10, daily_limit=50)
    asyncio.run(limiter.reset())
    app.dependency_overrides.clear()
