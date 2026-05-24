from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from irodori_service.config import Settings
from irodori_service.engine import IrodoriEngine
from tts_common.errors import ErrorBody, ErrorResponse
from tts_common.schemas import IrodoriVariant

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()
    engine = IrodoriEngine(cfg)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        _LOGGER.info(
            "Irodori service starting (base=%s, voice_design=%s)",
            cfg.base_hf_repo,
            cfg.voice_design_hf_repo,
        )
        yield

    app = FastAPI(title="tts-irodori", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "healthy",
            "loaded_variants": list(engine._runtimes.keys()),
            "base_repo": cfg.base_hf_repo,
            "voice_design_repo": cfg.voice_design_hf_repo,
        }

    async def _synthesize_from_fields(
        *,
        text: str,
        irodori_variant: str,
        caption: str | None,
        no_ref: bool,
        num_steps: int,
        seed: int | None,
        cfg_scale_text: float,
        cfg_scale_caption: float,
        cfg_scale_speaker: float,
        ref_audio: UploadFile | None,
    ) -> Response:
        variant = irodori_variant
        if variant not in (IrodoriVariant.BASE, IrodoriVariant.VOICE_DESIGN):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error=ErrorBody(
                        code="invalid_variant",
                        message=f"Unknown irodori_variant: {variant}",
                        engine="irodori",
                    )
                ).model_dump(),
            )

        if variant == IrodoriVariant.VOICE_DESIGN:
            if not caption or not caption.strip():
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error=ErrorBody(
                            code="caption_required",
                            message="caption is required for voice_design",
                            engine="irodori",
                        )
                    ).model_dump(),
                )
            no_ref = True
            ref_audio = None

        ref_path: str | None = None
        try:
            if ref_audio is not None and ref_audio.filename:
                content = await ref_audio.read()
                if len(content) > cfg.max_ref_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=ErrorResponse(
                            error=ErrorBody(
                                code="ref_audio_too_large",
                                message=f"ref_audio exceeds {cfg.max_ref_bytes} bytes",
                                engine="irodori",
                            )
                        ).model_dump(),
                    )
                suffix = Path(ref_audio.filename).suffix or ".wav"
                ref_path = engine.write_ref_audio(content, suffix)
                no_ref = False

            if variant == IrodoriVariant.BASE and not no_ref and ref_path is None:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error=ErrorBody(
                            code="ref_audio_required",
                            message="ref_audio or no_ref=true required for base variant",
                            engine="irodori",
                        )
                    ).model_dump(),
                )

            wav_bytes, meta = await run_in_threadpool(
                engine.synthesize_wav,
                variant=variant,
                text=text,
                caption=caption,
                ref_wav_path=ref_path,
                no_ref=no_ref,
                num_steps=num_steps,
                seed=seed,
                cfg_scale_text=cfg_scale_text,
                cfg_scale_caption=cfg_scale_caption,
                cfg_scale_speaker=cfg_scale_speaker,
            )
        except HTTPException:
            raise
        except Exception as exc:
            _LOGGER.exception("Irodori synthesis failed")
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=ErrorBody(
                        code="synthesis_failed",
                        message=str(exc),
                        engine="irodori",
                    )
                ).model_dump(),
            ) from exc
        finally:
            engine.cleanup_ref(ref_path)

        headers = {"X-TTS-Seed": str(meta.get("used_seed", ""))}
        if meta.get("stage_timings"):
            headers["X-TTS-Timings"] = json.dumps(meta["stage_timings"])
        return Response(content=wav_bytes, media_type="audio/wav", headers=headers)

    @app.post("/internal/synthesize")
    async def synthesize_multipart(
        text: str = Form(...),
        irodori_variant: str = Form(default="base"),
        caption: str | None = Form(default=None),
        no_ref: bool = Form(default=False),
        num_steps: int = Form(default=40),
        seed: int | None = Form(default=None),
        cfg_scale_text: float = Form(default=3.0),
        cfg_scale_caption: float = Form(default=3.0),
        cfg_scale_speaker: float = Form(default=5.0),
        ref_audio: UploadFile | None = File(default=None),
    ) -> Response:
        return await _synthesize_from_fields(
            text=text,
            irodori_variant=irodori_variant,
            caption=caption,
            no_ref=no_ref,
            num_steps=num_steps,
            seed=seed,
            cfg_scale_text=cfg_scale_text,
            cfg_scale_caption=cfg_scale_caption,
            cfg_scale_speaker=cfg_scale_speaker,
            ref_audio=ref_audio,
        )

    @app.post("/internal/synthesize/json")
    async def synthesize_json(body: dict[str, Any]) -> Response:
        """JSON body without ref audio (no_ref or pre-uploaded paths only)."""
        return await _synthesize_from_fields(
            text=str(body["text"]),
            irodori_variant=str(body.get("irodori_variant", "base")),
            caption=body.get("caption"),
            no_ref=bool(body.get("no_ref", False)),
            num_steps=int(body.get("num_steps", 40)),
            seed=body.get("seed"),
            cfg_scale_text=float(body.get("cfg_scale_text", 3.0)),
            cfg_scale_caption=float(body.get("cfg_scale_caption", 3.0)),
            cfg_scale_speaker=float(body.get("cfg_scale_speaker", 5.0)),
            ref_audio=None,
        )

    return app


app = create_app()
