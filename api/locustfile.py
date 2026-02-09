import base64
import os
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

from locust import HttpUser, between, events, tag, task

# Dataset configuration
DATASET_DIR = Path(os.getenv("LOCUST_DATASET_DIR", "../datasets")).resolve()
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_CACHE: list[tuple[str, str]] = []


# dataset_dir 아래의 모든 이미지 탐색
def discover_images(dataset_dir: Path) -> list[Path]:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"dataset dir not found: {dataset_dir}")

    paths = [
        p
        for p in dataset_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]

    if not paths:
        raise FileNotFoundError(
            f"No images found under: {dataset_dir} (exts={sorted(IMAGE_EXTS)})"
        )

    return paths


# dataset_dir 아래의 모든 이미지를 (relative_path_from_dataset_dir, base64) 로 캐싱
def build_cache(dataset_dir: Path) -> list[tuple[str, str]]:
    cache: list[tuple[str, str]] = []

    for img_path in discover_images(dataset_dir):
        image_id = str(img_path.relative_to(dataset_dir)).replace("\\", "/")
        image_b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        cache.append((image_id, image_b64))

    return cache


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    global IMAGE_CACHE
    IMAGE_CACHE = build_cache(DATASET_DIR)

    print("[locust] dataset initialized")
    print(f"[locust] dataset_dir     = {DATASET_DIR}")
    print(f"[locust] cached_images   = {len(IMAGE_CACHE)}")


def random_cached_image() -> tuple[str, str]:
    if not IMAGE_CACHE:
        raise RuntimeError("IMAGE_CACHE is empty. Did init hook run?")
    return random.choice(IMAGE_CACHE)


class BasicUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(5, 5)  # 각 유저의 요청 주기

    @tag("sync")
    @task
    def analyze_test(self):
        req_id = f"locust-{uuid.uuid4().hex}"
        image_id, image_b64 = random_cached_image()
        payload = {
            "request_id": req_id,
            "image_id": image_id,
            "image_base64": image_b64,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.post("/v1/analyze", json=payload, name="POST /v1/analyze")

    @tag("async")
    @task
    def analyze_async_test(self):
        req_id = f"locust-{uuid.uuid4().hex}"
        image_id, image_b64 = random_cached_image()
        payload = {
            "request_id": req_id,
            "image_id": image_id,
            "image_base64": image_b64,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.post(
            "/v1/analyze_async", json=payload, name="POST /v1/analyze_async"
        )
