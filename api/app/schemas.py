from pydantic import BaseModel, Field
from typing import Literal, List, Optional

Priority = Literal["high", "normal"]

class AnalyzeRequest(BaseModel):
    image_id: str = Field(..., examples=["fire_002.jpg", "base_001.jpg"])
    client_id: Optional[str] = None
    ts: Optional[str] = None

class DetectedObject(BaseModel):
    label: Literal["person", "vehicle", "fire", "smoke", "accident", "unknown"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox_xyxy: Optional[List[int]] = None

class AnalyzeResponse(BaseModel):
    image_id: str
    priority: Priority
    caption: str
    objects: List[DetectedObject]
    risk_score: float = Field(..., ge=0.0, le=1.0)
