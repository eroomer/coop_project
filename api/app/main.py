from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uuid

from .ai_pipeline import PipelineConfig, AIPipeline
from .schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeResult

def create_app(cfg: PipelineConfig) -> FastAPI:
    app = FastAPI(title="3D Digital Twin AI API", version="1.0.0")
    pipeline = AIPipeline(cfg)

    @app.get("/", response_class=HTMLResponse)
    def index():
        # Default path 처리 로직
        return 
        """
        """

    @app.post("/v1/analyze", response_model=AnalyzeResponse)
    def analyze(req: AnalyzeRequest):
        """
        Week3 behavior:
          - decode base64 image
          - save to local storage
          - write DB (images, analyses)
          - run sync AI pipeline (YOLO->crop->BLIP)
        """
        try:
            out = pipeline.run_from_base64(req.image_base64)
            image_bytes = out["image_bytes"]
            objects = out["objects"]
            caption = out["caption"]
            risk_level = out["risk_level"]

            safe_objects = []
            for o in objects:
                safe_objects.append({
                    "label": o.get("label", "unknown"),
                    "confidence": float(o.get("confidence", 0.0)),
                    "bbox_xyxy": o.get("bbox_xyxy"),
                })

            result = AnalyzeResult(
                result_id=str(uuid.uuid4()),
                image_id=req.image_id,
                risk_level=risk_level,  # "high" | "normal"
                objects=safe_objects,
                caption=caption,
            )

            return AnalyzeResponse(
                response_id=str(uuid.uuid4()),
                ok=True,
                result=result,
                error_code=None,
            )

        except Exception as e:
            return AnalyzeResponse(
                response_id=str(uuid.uuid4()),
                ok=False,
                result=None,
                error_code=f"INTERNAL_ERROR: {type(e).__name__}",
            )

    @app.get("/health")
    def health():
        return {"status": "ok", "yolo": cfg.use_yolo, "blip": cfg.use_blip}

    return app

def main():
    import argparse
    import uvicorn
    # 서버 실행 시 입력한 argument 파싱
    p = argparse.ArgumentParser()
    p.add_argument("--no-yolo", action="store_true")
    p.add_argument("--yolo-model", default="yolov8n.pt")
    p.add_argument("--no-blip", action="store_true")
    p.add_argument("--blip-model", default="Salesforce/blip-image-captioning-base")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    args = p.parse_args()

    cfg = PipelineConfig(
        use_yolo        = not args.no_yolo,
        yolo_model      = args.yolo_model,
        use_blip        = not args.no_blip,
        blip_model      = args.blip_model,
    )

    uvicorn.run(create_app(cfg), host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()

