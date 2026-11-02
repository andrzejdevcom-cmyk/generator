#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f frontend/dist/index.html || { echo 'Najpierw uruchom bash scripts/install.sh'; exit 1; }
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
