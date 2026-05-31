from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
import structlog

from app.config.settings import Settings, get_settings
from app.middleware.auth_middleware import get_current_user
from app.middleware.rate_limit import enforce_rate_limit
from app.models.auth_models import CurrentUser
from app.models.request_models import ScanType
from app.models.response_models import ErrorResponse, ExtractionResponse
from app.services.extraction_service import ExtractionService, get_extraction_service
from app.utils.image_utils import validate_file_metadata, validate_file_size, validate_image_bytes

router = APIRouter(prefix="/receipt", tags=["receipt"])
logger = structlog.get_logger(__name__)


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    responses={
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def extract_receipt(
    image: UploadFile = File(...),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
    scanType: ScanType = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
    _rate_limit: None = Depends(enforce_rate_limit),
    extraction_service: ExtractionService = Depends(get_extraction_service),
    settings: Settings = Depends(get_settings),
) -> ExtractionResponse:
    del latitude, longitude

    validate_file_metadata(image, settings)
    image_bytes = await image.read()
    await image.close()

    validate_file_size(image_bytes, settings)
    validate_image_bytes(image_bytes)

    start = time.perf_counter()

    logger.info(
        "receipt_extraction_started",
        user_id=current_user.user_id,
        scan_type=scanType.value,
        image_size_bytes=len(image_bytes),
    )

    try:
        result = await extraction_service.extract_items(image_bytes=image_bytes, scan_type=scanType)
    except TimeoutError as exc:
        logger.warning(
            "receipt_extraction_timeout",
            user_id=current_user.user_id,
            scan_type=scanType.value,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI processing timed out") from exc
    except Exception as exc:
        logger.exception(
            "receipt_extraction_failed",
            user_id=current_user.user_id,
            scan_type=scanType.value,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI processing failure") from exc

    elapsed_ms = (time.perf_counter() - start) * 1000
    confidence = getattr(result, "confidence", None)

    logger.info(
        "receipt_extraction_completed",
        user_id=current_user.user_id,
        scan_type=scanType.value,
        processing_time_ms=round(elapsed_ms, 2),
        extraction_confidence=confidence,
    )

    return result
