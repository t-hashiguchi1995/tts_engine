from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from piper_service.config import Settings
from piper_service.engine import PiperEngine
from tts_common.errors import ErrorBody, ErrorResponse

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


class PiperSynthesizeBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    speaker_id: int | None = None
    length_scale: float | None = Field(default=None, ge=0.1, le=3.0)
    noise_scale: float | None = Field(default=None, ge=0.0, le=2.0)
    noise_scale_w: float | None = Field(default=None, ge=0.0, le=2.0)
    language: str | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()
    engine = PiperEngine(cfg)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            await run_in_threadpool(engine.load)
            _LOGGER.info("Piper engine ready (model=%s)", cfg.model_name)
        except Exception as exc:
            _LOGGER.exception("Failed to load Piper model: %s", exc)
        yield

    app = FastAPI(title="tts-piper", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, Any]:
        if engine.ready:
            return {
                "status": "healthy",
                "model": cfg.model_name,
                "model_path": str(engine.model_path) if engine.model_path else None,
            }
        return {"status": "unhealthy", "detail": "model not loaded"}

    @app.post("/internal/synthesize")
    async def synthesize(body: PiperSynthesizeBody) -> Response:
        if not engine.ready:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error=ErrorBody(
                        code="model_not_ready",
                        message="Piper model is not loaded",
                        engine="piper",
                    )
                ).model_dump(),
            )
        try:
            wav_bytes = await run_in_threadpool(
                engine.synthesize_wav,
                body.text,
                speaker_id=body.speaker_id,
                length_scale=body.length_scale,
                noise_scale=body.noise_scale,
                noise_scale_w=body.noise_scale_w,
                language=body.language,
            )
        except Exception as exc:
            _LOGGER.exception("Piper synthesis failed")
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=ErrorBody(
                        code="synthesis_failed",
                        message=str(exc),
                        engine="piper",
                    )
                ).model_dump(),
            ) from exc
        return Response(content=wav_bytes, media_type="audio/wav")

    return app


app = create_app()
