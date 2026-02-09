import json
from pathlib import Path

from app.ai.pipeline import PipelineConfig


def load_cfg_from_file(path: str) -> PipelineConfig:
    data = json.loads(Path(path).read_text())
    return PipelineConfig(**data)
