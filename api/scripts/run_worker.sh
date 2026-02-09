#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

cd "$PROJECT_ROOT"

source .venv/bin/activate

# 기존 redis queue를 비우면서 worker 실행하는 옵션 (Default: 0)
: "${REDIS_CLEAN_ON_START:=0}"

if [[ "$REDIS_CLEAN_ON_START" == "1" ]]; then
  echo "[run_worker] cleaning broker queues (redis db 0)..."
  redis-cli -h 127.0.0.1 -p 6379 -n 0 DEL "analyze.default" "analyze.emergency" >/dev/null || true

  echo "[run_worker] cleaning result backend (redis db 1)..."
  redis-cli -h 127.0.0.1 -p 6379 -n 1 --scan --pattern "celery-task-meta-*" | \
    xargs -r redis-cli -h 127.0.0.1 -p 6379 -n 1 DEL >/dev/null || true
fi

exec celery -A app.celery.app.celery_app worker -l info \
  -Q analyze.emergency,analyze.default \
  --concurrency=2