from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from PIL import Image
import io
import base64

Label = Literal["person", "vehicle", "fire", "smoke", "accident", "unknown"]

# ai pipeline의 설정을 관리하기 위한 클래스입니다.
# 데이터 관리 표준인 @dataclass 데코레이터를 사용하고 실행 중 변경을 막기 위해 frozen=True 인자를 적용했습니다.
@dataclass(frozen=True)
class PipelineConfig:
    use_yolo: bool = True
    yolo_model: str = "yolov8n.pt"                                # dafualt: YOLOv8 Nano
    use_blip: bool = True
    blip_model: str = "Salesforce/blip-image-captioning-base"    # dafualt: BLIP Base

class AIPipeline:
    """
    Synchronous pipeline:
      input base64 -> bytes -> PIL
      YOLOv8n -> objects
      crop best -> BLIP base caption
      risk_level rule (fire/smoke/accident => high else normal)
    Default: stub mode unless dependencies installed.
    """

    # 서버 실행 시 
    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.mode = "stub"
       
        # YOLO
        self.yolo = None
        if cfg.use_yolo:
            try:
                from ultralytics import YOLO  # type: ignore
                self.yolo = YOLO(cfg.yolo_weights)
            except Exception:
                self.yolo = None
        
        # BLIP (base)
        self.blip_processor = None
        self.blip_model = None
        if cfg.use_blip:
            try:
                from transformers import BlipProcessor, BlipForConditionalGeneration  # type: ignore
                self.blip_processor = BlipProcessor.from_pretrained(cfg.blip_model_id)
                self.blip_model = BlipForConditionalGeneration.from_pretrained(cfg.blip_model_id)
            except Exception:
                self.blip_processor = None
                self.blip_model = None

    @staticmethod
    def decode_base64_image(image_base64: str) -> bytes:
        return base64.b64decode(image_base64)

    @staticmethod
    def pil_from_bytes(image_bytes: bytes) -> Image.Image:
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")

    @staticmethod
    def _crop_best(pil: Image.Image, objects: list[dict[str, Any]]) -> Image.Image:
        if not objects:
            return pil
        best = max(objects, key=lambda o: o.get("confidence", 0.0))
        bbox = best.get("bbox_xyxy")
        if not bbox or len(bbox) != 4:
            return pil
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(pil.width, x2); y2 = min(pil.height, y2)
        if x2 <= x1 or y2 <= y1:
            return pil
        return pil.crop((x1, y1, x2, y2))

    @staticmethod
    def _map_yolo_cls_to_label(cls_id: int) -> Label:
        # COCO 기준(간단 매핑). fine-tuning 시 바꿀 수 있게 분리해둠.
        # person=0, car=2, motorcycle=3, bus=5, truck=7 등
        if cls_id == 0:
            return "person"
        if cls_id in (2, 3, 5, 7):
            return "vehicle"
        return "unknown"

    def _run_yolo(self, pil: Image.Image) -> list[dict[str, Any]]:
        if self.yolo is None:
            # stub: 예제용
            return [
                {"label": "unknown", "confidence": 0.5, "bbox_xyxy": [0, 0, min(100, pil.width), min(100, pil.height)]}
            ]

        results = self.yolo(pil, verbose=False)
        r0 = results[0]
        objects: list[dict[str, Any]] = []
        for b in r0.boxes:
            xyxy = [int(x) for x in b.xyxy[0].tolist()]
            conf = float(b.conf[0])
            cls_id = int(b.cls[0])
            label = self._map_yolo_cls_to_label(cls_id)
            objects.append({"label": label, "confidence": conf, "bbox_xyxy": xyxy})
        return objects

    def _run_blip2(self, pil: Image.Image) -> str:
        if self.blip_model is None or self.blip_processor is None:
            return "stub caption: models not installed."

        inputs = self.blip_processor(images=pil, return_tensors="pt").to("cpu")
        out = self.blip_model.generate(**inputs, max_new_tokens=40)
        caption = self.blip_processor.decode(out[0], skip_special_tokens=True)
        return caption

    @staticmethod
    def _infer_risk(objects: list[dict[str, Any]]) -> str:
        # 3주차 명세에 맞춰 “fire/smoke/accident 키워드” 중심으로 high 판단
        labels = {o.get("label") for o in objects}
        if "fire" in labels or "smoke" in labels or "accident" in labels:
            return "high"
        return "normal"

    def run_from_base64(self, image_base64: str) -> dict[str, Any]:
        image_bytes = self.decode_base64_image(image_base64)
        pil = self.pil_from_bytes(image_bytes)

        objects = self._run_yolo(pil)
        crop = self._crop_best(pil, objects)
        caption = self._run_blip2(crop)

        risk_level = self._infer_risk(objects)

        return {
            "objects": objects,
            "caption": caption,
            "risk_level": risk_level,
            "pipeline_mode": self.mode,
            "image_bytes": image_bytes,  # 저장용으로 main.py에서 사용
        }
