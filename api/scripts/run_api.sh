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

HOST="${HOST:-}"
PORT="${PORT:-}"
RELOAD="${RELOAD:-}"

# config 파일이 있으면 우선 사용 (기존 동작 유지)
if [[ -f "$CONFIG_PATH" ]]; then
  if command -v jq >/dev/null 2>&1; then
    HOST="${HOST:-$(jq -r '.host' "$CONFIG_PATH")}"
    PORT="${PORT:-$(jq -r '.port' "$CONFIG_PATH")}"
    RELOAD="${RELOAD:-$(jq -r '.reload' "$CONFIG_PATH")}"
  else
    HOST="${HOST:-$(python -c 'import json; print(json.load(open("'"$CONFIG_PATH"'","r"))["host"])')}"
    PORT="${PORT:-$(python -c 'import json; print(json.load(open("'"$CONFIG_PATH"'","r"))["port"])')}"
    RELOAD="${RELOAD:-$(python -c 'import json; print(json.load(open("'"$CONFIG_PATH"'","r"))["reload"])')}"
  fi
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