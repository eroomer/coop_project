from pathlib import Path
from celery.signals import worker_process_init
from app.infra.config import load_cfg_from_file
from app.celery.worker_state import init_pipeline_once

@worker_process_init.connect
def _init_pipeline_on_worker_start(**kwargs):
    cfg_path = Path(__file__).resolve().parents[2] / "config/pipeline_config.json"
    cfg = load_cfg_from_file(str(cfg_path))
    init_pipeline_once(cfg)