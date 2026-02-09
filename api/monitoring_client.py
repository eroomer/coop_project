import json
import logging
import time

import redis
import requests
from app.celery.app import celery_config

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [monitor] %(message)s")

CHANNEL = "analysis:done"

# API 서버 주소
API_BASE = "http://127.0.0.1:8000"

# 결과 조회 재시도 정책
FETCH_MAX_ATTEMPTS = 30
FETCH_BASE_DELAY = 0.2
FETCH_MAX_DELAY = 2


# /v1/result_async/{task_id}를 호출해서 결과를 반환
def fetch_result_async(task_id: str) -> dict | None:
    url = f"{API_BASE}/v1/result_async/{task_id}"
    delay = FETCH_BASE_DELAY

    for attempt in range(1, FETCH_MAX_ATTEMPTS + 1):
        try:
            r = requests.get(url, timeout=3)
            r.raise_for_status()
            data = r.json()

            # 서버 구현상: PENDING이면 ok=True, result=None, error_code=PENDING
            error_code = data.get("error_code")
            result = data.get("result")

            if error_code == "PENDING" or result is None:
                logging.info(
                    f"result_async pending (attempt {attempt}/{FETCH_MAX_ATTEMPTS}) task_id={task_id}"
                )
            else:
                return data

        except requests.RequestException as e:
            logging.warning(
                f"result_async request failed (attempt {attempt}/{FETCH_MAX_ATTEMPTS}) task_id={task_id}: {e}"
            )

        time.sleep(delay)
        delay = min(delay * 1.5, FETCH_MAX_DELAY)

    logging.error(f"result_async fetch timeout: task_id={task_id}")
    return None


def main():
    try:
        redis_client = redis.Redis(
            host=celery_config["backend_ip"],
            port=celery_config["backend_port"],
            db=celery_config["backend_db"],
            decode_responses=True,
        )
        pubsub = redis_client.pubsub()
        pubsub.subscribe("analysis:done")

        logging.info("Subscribed to 'analysis:done' channel. Waiting for messages...")
        logging.info(f"API_BASE_URL={API_BASE}")

        while True:
            message = pubsub.get_message()
            if message and message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    task_id = payload.get("task_id")
                    status = payload.get("status")
                    ok = payload.get("ok")
                    err = payload.get("error")

                    logging.info(
                        f"task done: task_id={task_id} status={status} ok={ok} err={err}"
                    )

                    # 성공 시 API로 결과 조회
                    if status == "SUCCESS" and task_id:
                        data = fetch_result_async(task_id)
                        if data is not None:
                            result = data.get("result") or {}
                            logging.info(
                                f"fetched result: task_id={task_id} "
                                f"risk_level={result.get('risk_level')} "
                                f"caption={result.get('caption')}"
                            )
                        else:
                            logging.error(
                                f"failed to fetch result for task_id={task_id}"
                            )

                    # 실패 시 실패 로그
                    elif status == "FAILURE":
                        logging.warning(f"task failed: task_id={task_id} err={err}")

                except json.JSONDecodeError:
                    logging.warning("Failed to parse message payload. Skipping.")
                except Exception as e:
                    logging.error(f"Error processing message: {e}")

            time.sleep(0.1)  # Avoid busy-looping

    except redis.exceptions.ConnectionError as e:
        logging.error(f"Failed to connect to Redis: {e}")


if __name__ == "__main__":
    main()
