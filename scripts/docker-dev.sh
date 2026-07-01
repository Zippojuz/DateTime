#!/usr/bin/env bash
# Build and run the single combined dev container (Flask + Vite, hot reload).
# One command: builds the image, then runs it with source bind-mounted.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IMAGE="nexus-city:dev"

echo "==> Building $IMAGE"
docker build -t "$IMAGE" .

echo "==> Starting container (frontend :5173, backend :5000)"
echo "    Open http://localhost:5173 — Ctrl-C to stop."
exec docker run --init --rm \
  --name nexus-city-dev \
  -p 5173:5173 \
  -p 5000:5000 \
  -v "$ROOT":/app \
  -v nexus_node_modules:/app/frontend/node_modules \
  -e VITE_USE_POLLING=true \
  -e NEXUS_HOST=0.0.0.0 \
  "$IMAGE"
