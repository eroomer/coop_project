from app.celery_app import celery_app

@celery_app.task(name="app.tasks.analyze_task")
def analyze_task(request_id: str, image_id: str):
    # TODO: 나중에 YOLO/BLIP 파이프라인 연결
    return {"request_id": request_id, "image_id": image_id, "status": "queued"}