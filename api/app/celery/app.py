from celery import Celery
import json

with open("/home/ljh/coop_project/api/config/celery_config.json", "r") as f:
    celery_config = json.load(f)

celery_app = Celery(
    "app",
    broker=f"redis://{celery_config['broker_ip']}:{celery_config['broker_port']}/{celery_config['broker_db']}",
    backend=f"redis://{celery_config['backend_ip']}:{celery_config['backend_port']}/{celery_config['backend_db']}",  # 결과 저장
)

celery_app.conf.update(
    include=["app.celery.task"],
    task_default_queue="analyze.default",
    # prefetch 방지하여 우선 처리 순서 보장
    worker_prefetch_multiplier=1,
)
