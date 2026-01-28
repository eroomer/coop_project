from celery import Celery

celery_app = Celery(
    "app",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",  # 결과 저장
)

celery_app.conf.update(
    task_default_queue="analyze.default",
    task_routes={
        "app.tasks.analyze_task": {"queue": "analyze.default"},
    },
)