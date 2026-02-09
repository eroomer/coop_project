#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
CONFIG_PATH="$PROJECT_ROOT/config/api_config.json"

cd "$PROJECT_ROOT"
source .venv/bin/activate

# api_config.json에서 host/port/reload 읽기 (jq가 있으면 jq, 없으면 python fallback)
if command -v jq >/dev/null 2>&1; then
  HOST="$(jq -r '.host' "$CONFIG_PATH")"
  PORT="$(jq -r '.port' "$CONFIG_PATH")"
  RELOAD="$(jq -r '.reload' "$CONFIG_PATH")"
else
  HOST="$(python -c 'import json; print(json.load(open("'"$CONFIG_PATH"'","r"))["host"])')"
  PORT="$(python -c 'import json; print(json.load(open("'"$CONFIG_PATH"'","r"))["port"])')"
  RELOAD="$(python -c 'import json; print(json.load(open("'"$CONFIG_PATH"'","r"))["reload"])')"
fi

ARGS=(app.main:app --host "$HOST" --port "$PORT")

if [[ "$RELOAD" == "true" ]]; then
  ARGS+=(--reload)
fi

exec uvicorn "${ARGS[@]}"