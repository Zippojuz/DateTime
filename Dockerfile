# Single combined DEV container: Flask backend + Vite/React frontend with hot
# reload. Not a production image (see PLAN.md). node:22 gives Node 22; Debian
# bookworm provides Python 3.11.
FROM node:22-bookworm-slim

# System Python for the Flask backend.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Python venv at /opt/venv — outside /app (so it survives the source bind mount)
# and avoids Debian's PEP 668 "externally-managed-environment" pip block.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Backend deps (own layer for caching).
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

# Frontend deps (own layer for caching).
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci

# App source (host junk excluded via .dockerignore).
COPY . .

# Entrypoint runs both dev servers.
RUN chmod +x scripts/docker-start.sh

EXPOSE 5000 5173

CMD ["scripts/docker-start.sh"]
