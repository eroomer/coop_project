import threading
from typing import Optional

from app.ai.pipeline import AIPipeline, PipelineConfig

pipeline_lock = threading.Lock()
pipeline: Optional[AIPipeline] = None


def init_pipeline_once(cfg: PipelineConfig):
    global pipeline
    if pipeline is None:
        pipeline = AIPipeline(cfg)
