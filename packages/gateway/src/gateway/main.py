from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from gateway.auth import verify_api_key
from gateway.config import Settings
from gateway.router import route_synthesize
from gateway.security import RateLimitMiddleware, SecurityHeadersMiddleware
from tts_common.client import build_internal_headers, fetch_health
from tts_common.errors import ErrorBody, ErrorResponse
from tts_common.schemas import (
    Engine,
    EngineInfo,
    EnginesResponse,
    HealthResponse,
    IrodoriOptions,
    IrodoriVariant,
    PiperOptions,
    ServiceHealth,
    SynthesizeRequest,
)

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


def _check_upload_size(request: Request, settings: Settings) -> None:
    raw = request.headers.get("content-length")
    if raw is None:
        return
    try:
        size = int(raw)
    except ValueError:
        return
    if size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="payload_too_large",
                    message=f"Request body exceeds {settings.max_upload_bytes} bytes",
                )
            ).model_dump(),
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()
    cfg.validate_startup()
    http_client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal http_client
        http_client = httpx.AsyncClient()
        app.state.client = http_client
        app.state.settings = cfg
        _LOGGER.info(
            "Gateway started (require_api_keys=%s, rate_limit_rpm=%s)",
            cfg.require_api_keys,
            cfg.rate_limit_rpm,
        )
        yield
        await http_client.aclose()

    app = FastAPI(
        title="tts-engine-gateway",
        version="0.1.0",
        lifespan=lifespan,
        description="Unified TTS API for Piper-plus and Irodori-TTS",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=cfg)

    if cfg.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=sorted(cfg.allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            max_age=600,
        )

    def get_settings() -> Settings:
        return cfg

    def get_client() -> httpx.AsyncClient:
        return app.state.client

    @app.get("/health", response_model=HealthResponse)
    async def health(
        client: httpx.AsyncClient = Depends(get_client),
        settings: Settings = Depends(get_settings),
    ) -> HealthResponse:
        backends: dict[str, ServiceHealth] = {}
        overall = "healthy"

        for name, url, audience in (
            ("piper", settings.piper_service_url, settings.internal_iam_audience_piper),
            (
                "irodori",
                settings.irodori_service_url,
                settings.internal_iam_audience_irodori,
            ),
        ):
            try:
                headers = build_internal_headers(
                    use_iam=settings.internal_use_iam,
                    audience=audience or url,
                )
                data = await fetch_health(client, url, headers=headers)
                status_value = data.get("status", "unknown")
                backends[name] = ServiceHealth(status=status_value)
                if status_value != "healthy":
                    overall = "degraded"
            except Exception as exc:
                backends[name] = ServiceHealth(status="unhealthy", detail=str(exc))
                overall = "degraded"

        return HealthResponse(
            status=overall,
            gateway=ServiceHealth(status="healthy"),
            backends=backends,
        )

    @app.get("/v1/engines", response_model=EnginesResponse)
    def list_engines(
        authorization: str | None = Header(default=None),
        settings: Settings = Depends(get_settings),
    ) -> EnginesResponse:
        verify_api_key(settings, authorization)
        return EnginesResponse(
            engines=[
                EngineInfo(
                    id=Engine.PIPER,
                    description="Piper-plus ONNX (fast CPU TTS)",
                ),
                EngineInfo(
                    id=Engine.IRODORI,
                    description="Irodori-TTS v2 Flow Matching TTS",
                    variants=[v.value for v in IrodoriVariant],
                ),
            ]
        )

    @app.post("/v1/tts/synthesize")
    async def synthesize_json(
        body: SynthesizeRequest,
        authorization: str | None = Header(default=None),
        client: httpx.AsyncClient = Depends(get_client),
        settings: Settings = Depends(get_settings),
    ) -> Response:
        verify_api_key(settings, authorization)
        upstream = await route_synthesize(client, settings, body, ref_audio=None)
        return Response(
            content=upstream.content,
            media_type=upstream.headers.get("content-type", "audio/wav"),
            headers={
                k: v
                for k, v in upstream.headers.items()
                if k.lower().startswith("x-tts-")
            },
        )

    @app.post("/v1/tts/synthesize/multipart")
    async def synthesize_multipart(
        request: Request,
        text: str = Form(...),
        engine: Engine = Form(...),
        irodori_variant: IrodoriVariant | None = Form(default=None),
        caption: str | None = Form(default=None),
        no_ref: bool = Form(default=False),
        num_steps: int = Form(default=40),
        seed: int | None = Form(default=None),
        language: str | None = Form(default=None),
        speaker_id: int | None = Form(default=None),
        length_scale: float | None = Form(default=None),
        ref_audio: UploadFile | None = File(default=None),
        authorization: str | None = Header(default=None),
        client: httpx.AsyncClient = Depends(get_client),
        settings: Settings = Depends(get_settings),
    ) -> Response:
        verify_api_key(settings, authorization)
        _check_upload_size(request, settings)
        try:
            if engine == Engine.PIPER:
                req = SynthesizeRequest(
                    text=text,
                    engine=engine,
                    piper=PiperOptions(
                        language=language,
                        speaker_id=speaker_id,
                        length_scale=length_scale,
                    ),
                )
            else:
                req = SynthesizeRequest(
                    text=text,
                    engine=engine,
                    irodori=IrodoriOptions(
                        irodori_variant=irodori_variant or IrodoriVariant.BASE,
                        caption=caption,
                        no_ref=no_ref,
                        num_steps=num_steps,
                        seed=seed,
                    ),
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error=ErrorBody(code="validation_error", message=str(exc))
                ).model_dump(),
            ) from exc

        upstream = await route_synthesize(client, settings, req, ref_audio=ref_audio)
        return Response(
            content=upstream.content,
            media_type=upstream.headers.get("content-type", "audio/wav"),
            headers={
                k: v
                for k, v in upstream.headers.items()
                if k.lower().startswith("x-tts-")
            },
        )

    return app


app = create_app()
