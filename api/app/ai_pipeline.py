from __future__ import annotations
from typing import Any, Literal
from PIL import Image
import os
import io
import base64

Label = Literal["person", "vehicle", "fire", "smoke", "accident", "unknown"]

class AIPipeline:
    """
    Synchronous pipeline:
      input base64 -> bytes -> PIL
      YOLOv8n -> objects
      crop best -> BLIP-2 caption
      risk_level rule (fire/smoke/accident => high else normal)
    Default: stub mode unless dependencies installed.
    """

    def __init__(self):
        self.mode = "stub"

        self.yolo = None
        self.blip_processor = None
        self.blip_model = None

        # YOLO
        try:
            from ultralytics import YOLO  # type: ignore
            self.yolo = YOLO("yolov8n.pt")
            self.mode = "yolo_only"
        except Exception:
            self.yolo = None

        # BLIP-2 (optional)
        # - 기본값: 비활성화 (대용량 다운로드 방지)
        # - USE_BLIP=true 일 때만 실제 로드/다운로드
        USE_BLIP = os.getenv("USE_BLIP", "false").lower() == "true"

        if USE_BLIP:
            try:
                import torch  # type: ignore
                from transformers import Blip2Processor, Blip2ForConditionalGeneration  # type: ignore

                # ⚠️ 이 모델은 매우 큼(자동 다운로드). 정말 필요할 때만 USE_BLIP=true로 켜기.
                model_id = "Salesforce/blip2-opt-2.7b"
                self.blip_processor = Blip2Processor.from_pretrained(model_id)
                self.blip_model = Blip2ForConditionalGeneration.from_pretrained(model_id).to("cpu")

                self.mode = "yolo+blip2" if self.yolo else "blip2_only"
            except Exception:
                self.blip_processor = None
                self.blip_model = None
                # YOLO만 있으면 yolo_only, 아니면 stub
                if self.yolo:
                    self.mode = "yolo_only"
        else:
            self.blip_processor = None
            self.blip_model = None
            if self.yolo:
                self.mode = "yolo_only"


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
