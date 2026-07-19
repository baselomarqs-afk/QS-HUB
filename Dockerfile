# ──────────────────────────────────────────────────────────────────
# THE QS HUB — Multi-stage Dockerfile
# Stage 1: Build React frontend
# Stage 2: Serve FastAPI + built frontend
# ──────────────────────────────────────────────────────────────────

# ── Stage 1: Build React ──────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python API Server ────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn

# Create a non-root user for HuggingFace Spaces compatibility
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY --chown=user . $HOME/app/

# Copy built React into frontend/dist so FastAPI serves it
COPY --from=frontend-builder --chown=user /build/dist $HOME/app/frontend/dist

# Ensure writable directories exist
RUN mkdir -p $HOME/app/.qto_cache $HOME/app/.qto_storage && chmod -R 777 $HOME/app/.qto_cache $HOME/app/.qto_storage

EXPOSE 7860

CMD gunicorn api.main:app --workers 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:7860
