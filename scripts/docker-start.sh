#!/usr/bin/env bash
# Container entrypoint: run the Flask backend and Vite frontend side by side.
# Both share localhost inside the container, so Vite's /api proxy target works.
set -euo pipefail

# Backend — reads NEXUS_HOST (set to 0.0.0.0 by the run command) so it's
# reachable from the host.
(cd /app/backend && python app.py) &
backend_pid=$!

# Frontend — reads VITE_USE_POLLING for cross-platform file watching.
(cd /app/frontend && npm run dev) &
frontend_pid=$!

shutdown() {
  kill -TERM "$backend_pid" "$frontend_pid" 2>/dev/null || true
  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}
trap shutdown SIGINT SIGTERM

# If either dev server exits, tear the whole container down.
wait -n
shutdown
