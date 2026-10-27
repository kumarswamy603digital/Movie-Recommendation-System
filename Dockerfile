# syntax=docker/dockerfile:1
# Movie Recommendation System — backend image.
# Build from project root: docker build -f Dockerfile -t movierec-backend .

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System build tools for scipy / scikit-learn wheels (small cost, huge compat win)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for layer caching
COPY PROJECT2/backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copy app + scripts
COPY PROJECT2/backend/app ./app
COPY PROJECT2/backend/scripts ./scripts
COPY PROJECT2/backend/pytest.ini ./pytest.ini

# Bake dataset + pipeline into the image so first boot is fast and offline-safe.
# Remove these RUN lines if you prefer to mount data as a volume.
RUN mkdir -p data processed artifacts && \
    python -m scripts.download_dataset && \
    python -m scripts.preprocess_data && \
    python -m scripts.train_models && \
    python -m scripts.evaluate_models

ENV DATABASE_URL="sqlite:////data/app.db" \
    DATA_DIR="/data" \
    PROCESSED_DIR="/data/processed" \
    ARTIFACTS_DIR="/data/artifacts" \
    CORS_ORIGINS="http://localhost:5173" \
    LOG_LEVEL="INFO"

RUN mkdir -p /data/processed /data/artifacts && \
    cp -r data/* /data/ 2>/dev/null || true && \
    cp -r processed/* /data/processed/ 2>/dev/null || true && \
    cp -r artifacts/* /data/artifacts/ 2>/dev/null || true

EXPOSE 8000

# Healthcheck hits the versioned endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
