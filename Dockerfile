FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/models

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY kb_core ./kb_core
COPY kb_cli ./kb_cli
COPY scripts ./scripts

RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "python", "-c", "print('kb-local image ready')"]
