from .schemas import AnalyzeResponse, DetectedObject

EMERGENCY_KEYWORDS = ("fire", "smoke", "accident")

def build_stub_result(image_id: str) -> AnalyzeResponse:
    lower = image_id.lower()

    objects = []

    def add(label: str, conf: float, bbox):
        objects.append(
            DetectedObject(label=label, confidence=conf, bbox_xyxy=bbox)
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
        priority = "high"
        caption = "Emergency detected (stub)."
        risk_score = 0.95
    else:
        priority = "normal"
        if objects:
            caption = "Intrusion detected (stub)."
            risk_score = 0.65
        else:
            caption = "No critical events detected (stub)."
            risk_score = 0.05

    return AnalyzeResponse(
        image_id=image_id,
        priority=priority,
        caption=caption,
        objects=objects,
        risk_score=risk_score,
    )
