from locust import HttpUser, task, between
from datetime import datetime, timezone
from pathlib import Path
import base64
import uuid


def load_image_base64() -> str:
    api_dir = Path(__file__).resolve().parent  # .../coop_project/api
    img_path = (api_dir / "../datasets/base/base_001.jpg").resolve()

    if not img_path.exists():
        raise FileNotFoundError(
            f"이미지 파일을 찾을 수 없습니다: {img_path}\n"
            f"현재 locustfile 위치: {api_dir}\n"
            f"datasets가 api와 같은 레벨에 있는지 확인하세요."
        )

    img_bytes = img_path.read_bytes()
    return base64.b64encode(img_bytes).decode("ascii")

IMAGE_B64 = load_image_base64()

class BasicUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 1)       # 각 유저가 1초마다 요청

    # @task
    # def health_test(self):
    #     # /health 시도
    #     r = self.client.get("/health", name="GET /health")

    @task
    def analyze_test(self):
        req_id = f"locust-{uuid.uuid4().hex}"
        payload = {
            "request_id": req_id,
            "image_id": "base_001.jpg",
            "image_base64": IMAGE_B64,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.post("/v1/analyze", json=payload, name="POST /v1/analyze")