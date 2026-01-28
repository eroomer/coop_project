#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

cd "$PROJECT_ROOT"

source .venv/bin/activate

exec celery -A app.celery.app.celery_app worker -l info \
  -Q analyze.emergency,analyze.default \
  --concurrency=1