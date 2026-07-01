#!/usr/bin/env bash
# Idempotent dev environment setup: backend venv + deps, frontend node_modules.
# Safe to run repeatedly — it skips work that's already done.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend: Python venv + deps"
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
deactivate

echo "==> Frontend: npm install"
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
  npm install --no-audit --no-fund
else
  echo "    node_modules present — skipping (delete it to force reinstall)"
fi

echo "==> Done. Run backend: (cd backend && source .venv/bin/activate && python app.py)"
echo "         Run frontend: (cd frontend && npm run dev)"
