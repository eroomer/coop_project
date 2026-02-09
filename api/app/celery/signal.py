import logging
import time
from pathlib import Path

from celery import signals
from celery.signals import worker_process_init

from app.celery.redis_pub import publish_task_event
from app.celery.worker_state import init_pipeline_once
from app.infra.config import load_cfg_from_file


@worker_process_init.connect
def _init_pipeline_on_worker_start(**kwargs):
    cfg_path = Path(__file__).resolve().parents[2] / "config/pipeline_config.json"
    cfg = load_cfg_from_file(str(cfg_path))
    init_pipeline_once(cfg)


logger = logging.getLogger(__name__)

TASK_EVENT_CHANNEL = "analysis:done"


@signals.task_success.connect
def task_success_handler(sender, result, **kwargs):
    """
    Celery task 성공 시 Redis Pub/Sub으로 publish.
    """
    publish_task_event(
        channel=TASK_EVENT_CHANNEL,
        task_id=sender.request.id,
        status="SUCCESS",
        ok=True,
        error=None,
        ts=time.time(),
    )


@signals.task_failure.connect
def task_failure_handler(sender, exception, traceback, **kwargs):
    """
    Celery task 실패 시 Redis Pub/Sub으로 publish.
    """
    publish_task_event(
        channel=TASK_EVENT_CHANNEL,
        task_id=sender.request.id,
        status="FAILURE",
        ok=False,
        error=str(exception),
        ts=time.time(),
    )


# sinal 모듈이 import 된 것을 확인하는 log
logger.info("Celery signals registered.")
