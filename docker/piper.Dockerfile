FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY packages/tts_common /app/packages/tts_common
COPY packages/piper_service /app/packages/piper_service

RUN uv sync --package tts-piper-service --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0
ENV PORT=8080
ENV PIPER_MODELS_DIR=/models/piper
ENV PIPER_DOWNLOAD_ON_START=true

RUN mkdir -p /models/piper /app/output
RUN chown -R 1000:1000 /models/piper /app/output

USER 1000

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "piper_service"]
