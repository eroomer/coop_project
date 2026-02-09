from __future__ import annotations

import hashlib
import time
from pathlib import Path

# 실제 이미지 파일 저장 (db에는 파일 경로 저장)

# api/ 기준 경로
API_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = API_DIR / "storage"
IMAGES_DIR = STORAGE_DIR / "images"


def ensure_storage_dirs() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_image_bytes(image_bytes: bytes, ext: str = ".jpg") -> tuple[str, str]:
    """
    Returns:
      (relative_path_from_api_dir, sha256)
    e.g. ("storage/images/170..._abcd1234.jpg", "sha256...")
    """
    ensure_storage_dirs()

    digest = sha256_bytes(image_bytes)
    ts = int(time.time() * 1000)
    filename = f"{ts}_{digest[:12]}{ext}"
    abs_path = IMAGES_DIR / filename
    abs_path.write_bytes(image_bytes)

    rel_path = str(abs_path.relative_to(API_DIR))
    return rel_path, digest
