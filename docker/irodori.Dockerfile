FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip curl libsndfile1 git \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip uv

WORKDIR /app
COPY pyproject.toml uv.lock /app/
COPY packages/tts_common /app/packages/tts_common
COPY packages/irodori_service /app/packages/irodori_service
COPY vendor/Irodori-TTS /app/vendor/Irodori-TTS

RUN uv sync --package tts-irodori-service --no-dev --frozen

ENV PATH="/app/.venv/bin:$PATH"
ENV HOST=0.0.0.0
ENV PORT=8080
ENV IRODORI_MODEL_DEVICE=cuda
ENV IRODORI_CODEC_DEVICE=cuda
ENV IRODORI_MODEL_PRECISION=bf16
ENV HF_HOME=/models/huggingface

RUN groupadd -g 1000 app && useradd -u 1000 -g app -d /models -s /usr/sbin/nologin app \
    && mkdir -p /models/huggingface && chown -R app:app /models

ENV HOME=/models/huggingface
ENV HF_HOME=/models/huggingface

USER app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "irodori_service"]
