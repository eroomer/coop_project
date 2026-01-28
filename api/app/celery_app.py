from celery import Celery

celery_app = Celery(
    "app",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",  # 결과 저장
)

celery_app.conf.update(
    include=["app.task"],
    task_default_queue="analyze.default",
    # prefetch 방지하여 우선 처리 순서 보장
    worker_prefetch_multiplier=1,
)
