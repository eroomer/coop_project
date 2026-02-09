from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

RiskLevel = Literal["high", "normal"]


class ErrorCode(Enum):
    NONE = 0
    INTERNAL_ERROR = 1
    NOT_FOUND = 2
    PENDING = 3


class AnalyzeRequest(BaseModel):
    request_id: str
    image_id: str = Field(..., examples=["fire_002.jpg", "base_001.jpg"])
    image_base64: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyzeResponse(BaseModel):
    response_id: str
    ok: bool
    result: Optional["AnalyzeResult"] = None
    error_code: ErrorCode = ErrorCode.NONE
    error_message: Optional[str] = None


class AnalyzeResult(BaseModel):
    result_id: str
    image_id: str
    risk_level: RiskLevel
    objects: List["DetectedObject"]
    caption: str


class DetectedObject(BaseModel):
    label: Literal["person", "vehicle", "fire", "smoke", "accident", "unknown"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox_xyxy: Optional[List[int]] = None


class AnalyzeAsyncResponse(BaseModel):
    response_id: str
    ok: bool
    task_id: str
    queue: str
    error_code: ErrorCode = ErrorCode.NONE
    error_message: Optional[str] = None
