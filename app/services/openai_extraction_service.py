from __future__ import annotations

import json
import time

from openai import APITimeoutError, AsyncOpenAI
import structlog

from app.config.settings import Settings
from app.models.request_models import ScanType
from app.models.response_models import ExtractionFailureResponse, ExtractionResponse, ExtractionSuccessResponse
from app.prompts.grocery_extraction_prompt import get_grocery_extraction_prompt
from app.utils.image_utils import image_to_data_url


logger = structlog.get_logger(__name__)


class OpenAIExtractionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)

    async def extract(self, image_bytes: bytes, scan_type: ScanType) -> ExtractionResponse:
        if not self._settings.openai_api_key:
            logger.error(
                "openai_extraction_missing_api_key",
                scan_type=scan_type.value,
            )
            return ExtractionFailureResponse(message="OpenAI API key not configured")

        prompt = get_grocery_extraction_prompt(scan_type)
        data_url = image_to_data_url(image_bytes)

        logger.info(
            "openai_extraction_request_started",
            scan_type=scan_type.value,
            model=self._settings.openai_model,
            image_size_bytes=len(image_bytes),
            prompt_length=len(prompt),
        )

        request_start = time.perf_counter()

        try:
            response = await self._client.responses.create(
                model=self._settings.openai_model,
                temperature=0,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
            )
        except APITimeoutError as exc:
            elapsed_ms = (time.perf_counter() - request_start) * 1000
            logger.warning(
                "openai_extraction_request_timeout",
                scan_type=scan_type.value,
                model=self._settings.openai_model,
                openai_time_ms=round(elapsed_ms, 2),
            )
            raise TimeoutError("OpenAI request timed out") from exc
        except Exception:
            elapsed_ms = (time.perf_counter() - request_start) * 1000
            logger.exception(
                "openai_extraction_request_failed",
                scan_type=scan_type.value,
                model=self._settings.openai_model,
                openai_time_ms=round(elapsed_ms, 2),
            )
            raise

        elapsed_ms = (time.perf_counter() - request_start) * 1000
        logger.info(
            "openai_extraction_request_completed",
            scan_type=scan_type.value,
            model=self._settings.openai_model,
            openai_time_ms=round(elapsed_ms, 2),
            output_text_length=len((response.output_text or "")),
        )

        output_text = (response.output_text or "").strip()
        payload = self._safe_json_parse(output_text)

        logger.info(
            "openai_extraction_response_parsed",
            scan_type=scan_type.value,
            success=payload.get("success"),
            payload_keys=sorted(list(payload.keys())),
        )

        if payload.get("success") is True:
            payload["scanType"] = scan_type.value
            return ExtractionSuccessResponse.model_validate(payload)

        message = payload.get("message") or "Unable to confidently extract grocery items"
        return ExtractionFailureResponse(message=message)

    def _safe_json_parse(self, text: str) -> dict:
        if not text:
            logger.warning("openai_extraction_empty_output_text")
            return {"success": False, "message": "Unable to confidently extract grocery items"}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("openai_extraction_non_json_output")
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                logger.warning("openai_extraction_json_recovery_failed")
                return {"success": False, "message": "Unable to confidently extract grocery items"}
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("openai_extraction_json_recovery_parse_failed")
                return {"success": False, "message": "Unable to confidently extract grocery items"}
