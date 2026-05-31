from __future__ import annotations

import json

from openai import APITimeoutError, AsyncOpenAI

from app.config.settings import Settings
from app.models.request_models import ScanType
from app.models.response_models import ExtractionFailureResponse, ExtractionResponse, ExtractionSuccessResponse
from app.prompts.grocery_extraction_prompt import get_grocery_extraction_prompt
from app.utils.image_utils import image_to_data_url


class OpenAIExtractionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)

    async def extract(self, image_bytes: bytes, scan_type: ScanType) -> ExtractionResponse:
        if not self._settings.openai_api_key:
            return ExtractionFailureResponse(message="OpenAI API key not configured")

        prompt = get_grocery_extraction_prompt(scan_type)
        data_url = image_to_data_url(image_bytes)

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
            raise TimeoutError("OpenAI request timed out") from exc

        output_text = (response.output_text or "").strip()
        payload = self._safe_json_parse(output_text)

        if payload.get("success") is True:
            payload["scanType"] = scan_type.value
            return ExtractionSuccessResponse.model_validate(payload)

        message = payload.get("message") or "Unable to confidently extract grocery items"
        return ExtractionFailureResponse(message=message)

    def _safe_json_parse(self, text: str) -> dict:
        if not text:
            return {"success": False, "message": "Unable to confidently extract grocery items"}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return {"success": False, "message": "Unable to confidently extract grocery items"}
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {"success": False, "message": "Unable to confidently extract grocery items"}
