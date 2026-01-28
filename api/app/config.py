import json
from pathlib import Path
from app.ai_pipeline import PipelineConfig

def load_cfg_from_file(path: str) -> PipelineConfig:
    data = json.loads(Path(path).read_text())
    return PipelineConfig(**data)

def load_cfg_from_env() -> PipelineConfig:
    import os, json
    raw = os.getenv("PIPELINE_CFG_JSON")
    if not raw:
        raise RuntimeError("PIPELINE_CFG_JSON not set")
    return PipelineConfig(**json.loads(raw))