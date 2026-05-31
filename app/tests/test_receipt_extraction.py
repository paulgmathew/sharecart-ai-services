from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io

from fastapi.testclient import TestClient
import jwt
from PIL import Image

from app.config.settings import get_settings
from app.main import app
from app.models.request_models import ScanType
from app.models.response_models import ExtractionItem, ExtractionSuccessResponse
from app.services.extraction_service import get_extraction_service


class FakeExtractionService:
    async def extract_items(self, image_bytes: bytes, scan_type: ScanType):
        del image_bytes
        return ExtractionSuccessResponse(
            storeName="Walmart",
            confidence=0.93,
            scanType=scan_type,
            items=[ExtractionItem(name="Whole Milk", price=4.89, quantity="1", unit="gallon", confidence=0.96)],
        )


def create_png_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_token() -> str:
    settings = get_settings()
    payload = {
        "userId": "user-2",
        "email": "user2@test.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=20)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_receipt_extract_success() -> None:
    app.dependency_overrides[get_extraction_service] = lambda: FakeExtractionService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/receipt/extract",
        headers={"Authorization": f"Bearer {create_token()}"},
        data={"scanType": "RECEIPT"},
        files={"image": ("receipt.png", create_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["scanType"] == "RECEIPT"
    assert payload["items"][0]["name"] == "Whole Milk"

    app.dependency_overrides.clear()


def test_invalid_file_extension_returns_422() -> None:
    app.dependency_overrides[get_extraction_service] = lambda: FakeExtractionService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/receipt/extract",
        headers={"Authorization": f"Bearer {create_token()}"},
        data={"scanType": "PRICE_TAG"},
        files={"image": ("receipt.txt", create_png_bytes(), "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False

    app.dependency_overrides.clear()
