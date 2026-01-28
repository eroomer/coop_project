from __future__ import annotations

from uuid import uuid4

from app.schemas import AnalyzeResponse, AnalyzeResult, DetectedObject

EMERGENCY_KEYWORDS = ("fire", "smoke", "accident")


def build_stub_result(image_id: str) -> AnalyzeResponse:
    lower = image_id.lower()

    objects: list[DetectedObject] = []

    def add(label: str, conf: float, bbox_xyxy: list[int] | None):
        objects.append(
            DetectedObject(label=label, confidence=conf, bbox_xyxy=bbox_xyxy)
        )

    # 키워드 기반 객체 생성
    if "fire" in lower:
        add("fire", 0.97, [120, 80, 420, 360])
    if "smoke" in lower:
        add("smoke", 0.91, [80, 40, 520, 400])
    if "accident" in lower:
        add("accident", 0.93, [100, 70, 230, 300])
    if "person" in lower:
        add("person", 0.92, [200, 120, 280, 340])
    if "car" in lower or "vehicle" in lower:
        add("vehicle", 0.90, [150, 180, 450, 360])

    # emergency 판별: fire / smoke / accident 중 하나라도 있으면 high
    is_emergency = any(k in lower for k in EMERGENCY_KEYWORDS)

    if is_emergency:
        risk_level = "high"   # RiskLevel = Literal["high", "normal"]
        caption = "Emergency detected (stub)."
    else:
        risk_level = "normal"
        caption = "Intrusion detected (stub)." if objects else "No critical events detected (stub)."

    result = AnalyzeResult(
        result_id=str(uuid4()),
        image_id=image_id,
        risk_level=risk_level,
        objects=objects,
        caption=caption,
    )

    return AnalyzeResponse(
        response_id=str(uuid4()),
        ok=True,
        result=result,
        error_code=None,
    )
