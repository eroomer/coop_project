#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
CONFIG_PATH="${CONFIG_PATH:-$PROJECT_ROOT/config/api_config.json}"

cd "$PROJECT_ROOT"

# 로컬에서는 .venv를 쓰고, 도커에서는 없을 수 있으니 조건부
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

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

HOST="${HOST:-}"
PORT="${PORT:-}"
RELOAD="${RELOAD:-}"

# env가 없으면 config 기반으로 조립, 그래도 없으면 도커 기본값으로
if [[ -z "$HOST" ]]; then
  HOST="$(get_cfg host)"
fi
if [[ -z "$PORT" ]]; then
  PORT="$(get_cfg port)"
fi
if [[ -z "$RELOAD" ]]; then
  RELOAD="$(get_cfg reload)"
fi

# config도 env도 없으면 안전 기본값
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-false}"

ARGS=(app.main:app --host "$HOST" --port "$PORT")

if [[ "$RELOAD" == "true" ]]; then
  ARGS+=(--reload)
fi

exec uvicorn "${ARGS[@]}"