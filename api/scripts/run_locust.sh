#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

cd "$PROJECT_ROOT"
source .venv/bin/activate

export LOCUST_DATASET_DIR="$(realpath "$PROJECT_ROOT/../datasets")"

locust "$@"