import json
from pathlib import Path
from app.ai_pipeline import PipelineConfig

def load_cfg_from_file(path: str) -> PipelineConfig:
    data = json.loads(Path(path).read_text())
    return PipelineConfig(**data)