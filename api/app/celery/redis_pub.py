import json
import logging

import redis

from app.celery.app import celery_config

logger = logging.getLogger(__name__)


# celery_config.json 기반으로 redis client 생성
def redis_client_from_config(config: dict) -> redis.Redis | None:
    try:
        client = redis.Redis(
            host=config["backend_ip"],
            port=config["backend_port"],
            db=config["backend_db"],
            decode_responses=True,
        )
        client.ping()  # Check connection
        return client
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        return None


# task 완료 event publish
def publish_task_event(
    channel: str, task_id: str, status: str, ok: bool, error: str | None, ts: float
):
    try:
        redis_client = redis_client_from_config(celery_config)
        if redis_client:
            payload = {
                "task_id": task_id,
                "status": status,
                "ok": ok,
                "error": error,
                "ts": ts,
            }
            redis_client.publish(channel, json.dumps(payload))
            logger.info(f"Published task event to channel '{channel}': {payload}")
        else:
            logger.warning("Redis client not initialized. Skipping publish.")
    except Exception as e:
        logger.warning(f"Failed to publish task event: {e}")
