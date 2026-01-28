from locust import HttpUser, task, between
import uuid

class BasicUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 1)       # 각 유저가 1초마다 요청

    @task
    def health(self):
        # /health 시도
        r = self.client.get("/health", name="GET /health")

