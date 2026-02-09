import json
from pathlib import Path

from celery import Celery

cfg_path = Path(__file__).resolve().parents[2] / "config/celery_config.json"
celery_config = json.loads(cfg_path.read_text())

celery_app = Celery(
    "app",
    broker=f"redis://{celery_config['broker_ip']}:{celery_config['broker_port']}/{celery_config['broker_db']}",
    backend=f"redis://{celery_config['backend_ip']}:{celery_config['backend_port']}/{celery_config['backend_db']}",  # 결과 저장
)
# register celery signals (side-effect import)
# celery_app 생성 후에 signal 모듈을 import하기 위해 뒤에 둠
import app.celery.signal

celery_app.conf.update(
    include=["app.celery.task"],
    task_default_queue="analyze.default",
    # prefetch 방지하여 우선 처리 순서 보장
    worker_prefetch_multiplier=1,
)
