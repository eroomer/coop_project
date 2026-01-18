from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import threading
import uuid

from .ai_pipeline import PipelineConfig, AIPipeline
from .schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeResult
from .db import init_db, insert_image, insert_analysis, get_analysis
from .storage import ensure_storage_dirs, save_image_bytes

def create_app(cfg: PipelineConfig) -> FastAPI:
    app = FastAPI(title="3D Digital Twin AI API", version="1.0.0")
    pipeline = AIPipeline(cfg)

    @app.on_event("startup")
    def on_startup():
        ensure_storage_dirs()
        init_db()
        # pipeline을 app state에 저장 (프로세스당 1개)
        app.state.pipeline = AIPipeline(cfg)
        # thread-safe를 위해 lock도 같이 저장
        app.state.pipeline_lock = threading.Lock()

    @app.get("/health")
    def health():
        return {"status": "ok", "yolo": cfg.use_yolo, "blip": cfg.use_blip}

    @app.get("/", response_class=HTMLResponse)
    def index():
        # Default path 처리 로직
        return """
        <!doctype html>
        <html lang="ko">
        <body>API 서버입니다.</body>
        </html>
        """

    @app.post("/v1/analyze", response_model=AnalyzeResponse)
    def analyze(req: AnalyzeRequest, request: Request):
        """
        Week3 behavior:
          - decode base64 image
          - save to local storage
          - write DB (images, analyses)
          - run sync AI pipeline (YOLO->crop->BLIP)
        """
        try:
            # 0) AI pipeline에 접근하기 전 lock 획득 
            lock: threading.Lock = request.app.state.pipeline_lock

            # 1) AI pipeline 실행
            with lock:
                pipeline: AIPipeline = request.app.state.pipeline
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

            # 2) 파일 저장 (storage.py)
            rel_path, sha256 = save_image_bytes(image_bytes, ext=".jpg")

            # 4) DB 저장 (db.py)
            image_ref_id = insert_image(
                image_id=req.image_id,
                path=rel_path,
                sha256=sha256,
            )

            analysis_id = insert_analysis(
                request_id=req.request_id,       # trace용
                image_ref_id=image_ref_id,
                risk_level=risk_level,
                objects=safe_objects,
                caption=caption,        # DB schema가 NOT NULL이면 안전하게 빈 문자열
            )

            result = AnalyzeResult(
                result_id=str(analysis_id),
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

    @app.get("/v1/result/{analysis_id}")
    def get_result(analysis_id: int):
        """
        DB 조회용
        """
        data = get_analysis(analysis_id)
        if data is None:
            return {"ok": False, "error_code": "NOT_FOUND"}
        return {"ok": True, "data": data}

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

