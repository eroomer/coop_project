#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

exec celery -A app.celery_app.celery_app worker -l info \
  -Q analyze.emergency,analyze.default \
  --concurrency=1