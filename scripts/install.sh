#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.cache/pip}"
python -c 'import sys; assert sys.version_info[:2] == (3, 12), "Wymagany Python 3.12"'
node -e 'const v=+process.versions.node.split(".")[0];if(v<22||v>=25)throw Error("Wymagany Node.js 22–24")'
if [ ! -x .venv/bin/python ]; then python -m venv .venv; fi
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
npm --prefix frontend ci --cache "$PWD/.cache/npm" --no-audit --no-fund
npm --prefix frontend run build
.venv/bin/python -c 'from backend.geometry.engine import generate; from backend.models import Project; r=generate(Project()); assert r.valid and all(p.mesh.is_volume for p in r.parts); print("Geometria A: OK")'
