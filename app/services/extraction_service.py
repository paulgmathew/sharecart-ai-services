from __future__ import annotations

from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.models.request_models import ScanType
from app.models.response_models import ExtractionFailureResponse, ExtractionResponse, ExtractionSuccessResponse
from app.services.image_preprocessing_service import ImagePreprocessingService
from app.services.openai_extraction_service import OpenAIExtractionService


class ExtractionService:
    def __init__(self, preprocess_service: ImagePreprocessingService, ai_service: OpenAIExtractionService) -> None:
        self._preprocess_service = preprocess_service
        self._ai_service = ai_service

    async def extract_items(self, image_bytes: bytes, scan_type: ScanType) -> ExtractionResponse:
        processed = await self._preprocess_service.preprocess(image_bytes)
        result = await self._ai_service.extract(processed, scan_type)

        if isinstance(result, ExtractionSuccessResponse) and result.confidence < 0.35:
            return ExtractionFailureResponse(message="Unable to confidently extract grocery items")

        return result


@lru_cache(maxsize=1)
def get_extraction_service() -> ExtractionService:
    settings: Settings = get_settings()
    preprocess_service = ImagePreprocessingService(settings)
    ai_service = OpenAIExtractionService(settings)
    return ExtractionService(preprocess_service, ai_service)
