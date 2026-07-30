from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, Field

from app.models.request_models import ScanType


class ExtractionItem(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    quantity: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


class ExtractionSuccessResponse(BaseModel):
    success: bool = True
    storeName: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    scanType: ScanType
    items: list[ExtractionItem]


class ExtractionFailureResponse(BaseModel):
    success: bool = False
    message: str


ExtractionResponse = Union[ExtractionSuccessResponse, ExtractionFailureResponse]


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
