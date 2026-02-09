#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
CONFIG_PATH="$PROJECT_ROOT/config/celery_config.json"

cd "$PROJECT_ROOT"
source .venv/bin/activate

# 기존 redis queue를 비우면서 worker 실행하는 옵션 (Default: 0)
: "${REDIS_CLEAN_ON_START:=0}"

# ---- config loader (jq 우선, 없으면 python fallback) ----
get_cfg() {
  local key="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -r ".$key" "$CONFIG_PATH"
  else
    python3 -c "import json; print(json.load(open('$CONFIG_PATH'))['$key'])"
  fi
}

BROKER_IP="$(get_cfg broker_ip)"
BROKER_PORT="$(get_cfg broker_port)"
BROKER_DB="$(get_cfg broker_db)"

BACKEND_IP="$(get_cfg backend_ip)"
BACKEND_PORT="$(get_cfg backend_port)"
BACKEND_DB="$(get_cfg backend_db)"

# ---- optional redis cleanup ----
if [[ "$REDIS_CLEAN_ON_START" == "1" ]]; then
  echo "[run_worker] cleaning broker queues (redis db ${BROKER_DB}) @ ${BROKER_IP}:${BROKER_PORT} ..."
  redis-cli -h "$BROKER_IP" -p "$BROKER_PORT" -n "$BROKER_DB" \
    DEL "analyze.default" "analyze.emergency" >/dev/null || true

  echo "[run_worker] cleaning result backend (redis db ${BACKEND_DB}) @ ${BACKEND_IP}:${BACKEND_PORT} ..."
  redis-cli -h "$BACKEND_IP" -p "$BACKEND_PORT" -n "$BACKEND_DB" \
    --scan --pattern "celery-task-meta-*" | \
    xargs -r redis-cli -h "$BACKEND_IP" -p "$BACKEND_PORT" -n "$BACKEND_DB" DEL >/dev/null || true
fi

exec celery -A app.celery.app.celery_app worker -l info \
  -Q analyze.emergency,analyze.default \
  --concurrency=2