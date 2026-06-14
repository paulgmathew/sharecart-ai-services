from __future__ import annotations

from functools import lru_cache
import time

import structlog

from app.config.settings import Settings, get_settings
from app.models.request_models import ScanType
from app.models.response_models import ExtractionFailureResponse, ExtractionResponse, ExtractionSuccessResponse
from app.services.image_preprocessing_service import ImagePreprocessingService
from app.services.openai_extraction_service import OpenAIExtractionService


logger = structlog.get_logger(__name__)


class ExtractionService:
    def __init__(self, preprocess_service: ImagePreprocessingService, ai_service: OpenAIExtractionService) -> None:
        self._preprocess_service = preprocess_service
        self._ai_service = ai_service

    async def extract_items(self, image_bytes: bytes, scan_type: ScanType) -> ExtractionResponse:
        pipeline_start = time.perf_counter()
        logger.info(
            "extraction_pipeline_started",
            scan_type=scan_type.value,
            input_size_bytes=len(image_bytes),
        )

        preprocess_start = time.perf_counter()
        processed = await self._preprocess_service.preprocess(image_bytes)
        preprocess_elapsed_ms = (time.perf_counter() - preprocess_start) * 1000
        logger.info(
            "extraction_pipeline_preprocessing_completed",
            scan_type=scan_type.value,
            input_size_bytes=len(image_bytes),
            processed_size_bytes=len(processed),
            preprocessing_time_ms=round(preprocess_elapsed_ms, 2),
        )

        ai_start = time.perf_counter()
        result = await self._ai_service.extract(processed, scan_type)
        ai_elapsed_ms = (time.perf_counter() - ai_start) * 1000
        logger.info(
            "extraction_pipeline_ai_completed",
            scan_type=scan_type.value,
            ai_time_ms=round(ai_elapsed_ms, 2),
            extraction_success=isinstance(result, ExtractionSuccessResponse),
        )

        if isinstance(result, ExtractionSuccessResponse) and result.confidence < 0.35:
            logger.warning(
                "extraction_pipeline_low_confidence",
                scan_type=scan_type.value,
                confidence=result.confidence,
                threshold=0.35,
            )
            return ExtractionFailureResponse(message="Unable to confidently extract grocery items")

        pipeline_elapsed_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            "extraction_pipeline_completed",
            scan_type=scan_type.value,
            total_time_ms=round(pipeline_elapsed_ms, 2),
            extraction_success=isinstance(result, ExtractionSuccessResponse),
        )

        return result


@lru_cache(maxsize=1)
def get_extraction_service() -> ExtractionService:
    settings: Settings = get_settings()
    preprocess_service = ImagePreprocessingService(settings)
    ai_service = OpenAIExtractionService(settings)
    return ExtractionService(preprocess_service, ai_service)
