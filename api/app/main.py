import threading
import uuid

from celery.result import AsyncResult
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from app.ai.pipeline import AIPipeline
from app.celery.app import celery_app
from app.celery.task import analyze_task
from app.infra.config import load_cfg_from_file
from app.infra.db import get_analysis, init_db, insert_analysis, insert_image
from app.infra.storage import ensure_storage_dirs, save_image_bytes
from app.schemas import (
    AnalyzeAsyncResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeResult,
    ErrorCode,
)

PIPELINE_CONFIG_PATH = "/home/ljh/coop_project/api/config/pipeline_config.json"

app = FastAPI(title="3D Digital Twin AI API", version="1.1.0")


@app.on_event("startup")
def on_startup():
    ensure_storage_dirs()
    init_db()
    cfg = load_cfg_from_file(PIPELINE_CONFIG_PATH)
    # 동기 처리를 위한 pipeline을 app state에 저장 (프로세스당 1개)
    app.state.pipeline = AIPipeline(cfg)
    # thread-safe를 위해 lock도 같이 저장
    app.state.pipeline_lock = threading.Lock()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index():
    # Default path 처리 로직
    return """
    <!doctype html>
    <html lang="ko">
    <body>API 서버입니다.</body>
    </html>
    """


# 동기 처리
@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, request: Request):
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
            safe_objects.append(
                {
                    "label": o.get("label", "unknown"),
                    "confidence": float(o.get("confidence", 0.0)),
                    "bbox_xyxy": o.get("bbox_xyxy"),
                }
            )

        # 2) 파일 저장 (storage.py)
        rel_path, sha256 = save_image_bytes(image_bytes, ext=".jpg")

        # 4) DB 저장 (db.py)
        image_ref_id = insert_image(
            image_id=req.image_id,
            path=rel_path,
            sha256=sha256,
        )

        analysis_id = insert_analysis(
            request_id=req.request_id,  # trace용
            image_ref_id=image_ref_id,
            risk_level=risk_level,
            objects=safe_objects,
            caption=caption,  # DB schema가 NOT NULL이면 안전하게 빈 문자열
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
            error_code=ErrorCode.INTERNAL_ERROR,
            error_message=str(e),
        )


# 비동기 처리
@app.post("/v1/analyze_async", response_model=AnalyzeAsyncResponse)
def analyze_async(req: AnalyzeRequest):
    # 우선순위 규칙: image_id에 emergency 포함이면 긴급 큐
    queue_name = (
        "analyze.emergency" if "emergency" in req.image_id else "analyze.default"
    )

    # Celery task를 특정 큐로 라우팅 (Redis에 해당 큐로 저장됨)
    async_result = analyze_task.apply_async(
        args=[req.request_id, req.image_id, req.image_base64],
        queue=queue_name,
    )

    return AnalyzeAsyncResponse(
        response_id=str(uuid.uuid4()),
        ok=True,
        task_id=async_result.id,
        queue=queue_name,
        error_code=None,
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


@app.get("/v1/result_async/{task_id}", response_model=AnalyzeResponse)
def result_async(task_id: str):
    """
    Celery task_id로 비동기 분석 결과 조회
    """
    ar = AsyncResult(task_id, app=celery_app)

    # 아직 실행 전/실행 중
    if ar.state in ("PENDING", "RECEIVED", "STARTED", "RETRY"):
        return AnalyzeResponse(
            response_id=str(uuid.uuid4()),
            ok=True,
            result=None,
            error_code=ErrorCode.PENDING,
        )

    # 실패
    if ar.state == "FAILURE":
        return AnalyzeResponse(
            response_id=str(uuid.uuid4()),
            ok=False,
            result=None,
            error_code=ErrorCode.INTERNAL_ERROR,
            error_message="task failed: celery worker",
        )

    # 성공
    try:
        payload = ar.get()
    except Exception as e:
        return AnalyzeResponse(
            response_id=str(uuid.uuid4()),
            ok=False,
            result=None,
            error_code=ErrorCode.INTERNAL_ERROR,
            error_message=str(e),
        )
    return payload
