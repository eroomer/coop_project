#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
CONFIG_PATH="${CONFIG_PATH:-$PROJECT_ROOT/config/celery_config.json}"

cd "$PROJECT_ROOT"

# 로컬에서는 .venv를 쓰고, 도커에서는 없을 수 있으니 조건부
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# 기존 redis queue를 비우면서 worker 실행하는 옵션 (Default: 0)
: "${REDIS_CLEAN_ON_START:=0}"

# 워커 옵션도 env로 override 가능하게
: "${CELERY_CONCURRENCY:=2}"
: "${CELERY_LOGLEVEL:=info}"
: "${CELERY_QUEUES:=analyze.emergency,analyze.default}"

# ---- config loader (jq 우선, 없으면 python fallback) ----
get_cfg() {
  local key="$1"
  if [[ -f "$CONFIG_PATH" ]]; then
    if command -v jq >/dev/null 2>&1; then
      jq -r ".$key" "$CONFIG_PATH"
    else
      python3 -c "import json; print(json.load(open('$CONFIG_PATH'))['$key'])"
    fi
  else
    echo ""
  fi
}

# ---- broker/backend URL 결정 (env 우선, 없으면 config 기반) ----

CELERY_BROKER_URL="${CELERY_BROKER_URL:-}"
CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-}"

# config로부터 ip/port/db 읽기 (없으면 빈 문자열)
BROKER_IP="$(get_cfg broker_ip)"
BROKER_PORT="$(get_cfg broker_port)"
BROKER_DB="$(get_cfg broker_db)"

BACKEND_IP="$(get_cfg backend_ip)"
BACKEND_PORT="$(get_cfg backend_port)"
BACKEND_DB="$(get_cfg backend_db)"

# env가 없으면 config 기반으로 조립, 그래도 없으면 도커 기본값으로
if [[ -z "$CELERY_BROKER_URL" ]]; then
  if [[ -n "$BROKER_IP" && -n "$BROKER_PORT" && -n "$BROKER_DB" ]]; then
    CELERY_BROKER_URL="redis://${BROKER_IP}:${BROKER_PORT}/${BROKER_DB}"
  else
    CELERY_BROKER_URL="redis://redis:6379/0"
  fi
fi

if [[ -z "$CELERY_RESULT_BACKEND" ]]; then
  if [[ -n "$BACKEND_IP" && -n "$BACKEND_PORT" && -n "$BACKEND_DB" ]]; then
    CELERY_RESULT_BACKEND="redis://${BACKEND_IP}:${BACKEND_PORT}/${BACKEND_DB}"
  else
    CELERY_RESULT_BACKEND="redis://redis:6379/1"
  fi
fi

export CELERY_BROKER_URL
export CELERY_RESULT_BACKEND

# ---- optional redis cleanup ----
# (주의) 컨테이너에 redis-cli가 없을 수 있음. 있을 때만 수행.
if [[ "$REDIS_CLEAN_ON_START" == "1" ]]; then
  if ! command -v redis-cli >/dev/null 2>&1; then
    echo "[run_worker] REDIS_CLEAN_ON_START=1 but redis-cli not found; skipping cleanup."
  else
    # config 값이 있으면 그걸 쓰고, 없으면 URL로부터 호스트/포트/DB를 간단 파싱
    parse_redis_url() {
      # input: redis://host:port/db
      local url="$1"
      local hostport db
      hostport="${url#redis://}"
      db="${hostport##*/}"
      hostport="${hostport%/*}"
      echo "$hostport" "$db"
    }

    # broker cleanup 파라미터 결정
    if [[ -n "$BROKER_IP" && -n "$BROKER_PORT" && -n "$BROKER_DB" ]]; then
      CLEAN_BROKER_IP="$BROKER_IP"; CLEAN_BROKER_PORT="$BROKER_PORT"; CLEAN_BROKER_DB="$BROKER_DB"
    else
      read -r hostport db <<<"$(parse_redis_url "$CELERY_BROKER_URL")"
      CLEAN_BROKER_IP="${hostport%:*}"
      CLEAN_BROKER_PORT="${hostport##*:}"
      CLEAN_BROKER_DB="$db"
    fi

    # backend cleanup 파라미터 결정
    if [[ -n "$BACKEND_IP" && -n "$BACKEND_PORT" && -n "$BACKEND_DB" ]]; then
      CLEAN_BACKEND_IP="$BACKEND_IP"; CLEAN_BACKEND_PORT="$BACKEND_PORT"; CLEAN_BACKEND_DB="$BACKEND_DB"
    else
      read -r hostport db <<<"$(parse_redis_url "$CELERY_RESULT_BACKEND")"
      CLEAN_BACKEND_IP="${hostport%:*}"
      CLEAN_BACKEND_PORT="${hostport##*:}"
      CLEAN_BACKEND_DB="$db"
    fi

    echo "[run_worker] cleaning broker queues (redis db ${CLEAN_BROKER_DB}) @ ${CLEAN_BROKER_IP}:${CLEAN_BROKER_PORT} ..."
    redis-cli -h "$CLEAN_BROKER_IP" -p "$CLEAN_BROKER_PORT" -n "$CLEAN_BROKER_DB" \
      DEL "analyze.default" "analyze.emergency" >/dev/null || true

    echo "[run_worker] cleaning result backend (redis db ${CLEAN_BACKEND_DB}) @ ${CLEAN_BACKEND_IP}:${CLEAN_BACKEND_PORT} ..."
    redis-cli -h "$CLEAN_BACKEND_IP" -p "$CLEAN_BACKEND_PORT" -n "$CLEAN_BACKEND_DB" \
      --scan --pattern "celery-task-meta-*" | \
      xargs -r redis-cli -h "$CLEAN_BACKEND_IP" -p "$CLEAN_BACKEND_PORT" -n "$CLEAN_BACKEND_DB" DEL >/dev/null || true
  fi
fi

exec celery -A app.celery.app.celery_app worker -l "$CELERY_LOGLEVEL" \
  -Q "$CELERY_QUEUES" \
  --concurrency="$CELERY_CONCURRENCY"