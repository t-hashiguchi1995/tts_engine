FROM python:3.11-slim-bookworm AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY packages/tts_common /app/packages/tts_common
COPY packages/gateway /app/packages/gateway

RUN uv sync --package tts-gateway --extra gcp --no-dev --no-editable

FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip wheel 'jaraco.context>=6.1.0'

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "gateway"]
