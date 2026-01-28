from celery.signals import worker_process_init
from app.config import load_cfg_from_env
from app.worker_state import init_pipeline_once

@worker_process_init.connect
def _init_pipeline_on_worker_start(**kwargs):
    cfg = load_cfg_from_env()
    init_pipeline_once(cfg)