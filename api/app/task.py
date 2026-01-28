import uuid

# worker 시작 시 pipeline을 초기화하는 시그널
import app.celery_signal

from app.celery_app import celery_app
from app.worker_state import pipeline, pipeline_lock

from app.storage import save_image_bytes
from app.db import insert_image, insert_analysis


@celery_app.task(name="app.tasks.analyze_task")
def analyze_task(request_id: str, image_id: str, image_base64: str):
    """
    기존 동기 analyze와 동일한 동작을 Celery worker에서 수행.
    (YOLO->crop->BLIP -> storage 저장 -> DB 저장)
    """
    if pipeline is None:
        raise RuntimeError("Worker pipeline is not initialized. Check celery_signals/worker init.")

    # 1) AI pipeline 실행 (프로세스 내 1개 pipeline에 대해 lock 보호)
    with pipeline_lock:
        out = pipeline.run_from_base64(image_base64)

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

    # 2) 파일 저장
    rel_path, sha256 = save_image_bytes(image_bytes, ext=".jpg")

    # 3) DB 저장
    image_ref_id = insert_image(
        image_id=image_id,
        path=rel_path,
        sha256=sha256,
    )

    analysis_id = insert_analysis(
        request_id=request_id,
        image_ref_id=image_ref_id,
        risk_level=risk_level,
        objects=safe_objects,
        caption=caption,
    )

    # 4) 결과(AnalyzeResponse 형태로 쓰기 좋게) 반환
    return {
        "response_id": str(uuid.uuid4()),
        "ok": True,
        "result": {
            "result_id": str(analysis_id),
            "image_id": image_id,
            "risk_level": risk_level,
            "objects": safe_objects,
            "caption": caption,
        },
        "error_code": None,
    }
