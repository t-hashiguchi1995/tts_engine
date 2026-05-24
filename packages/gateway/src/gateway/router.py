from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile, status

from gateway.config import Settings
from tts_common.client import (
    build_internal_headers,
    parse_error_response,
    post_synthesize_json,
    post_synthesize_multipart,
)
from tts_common.errors import ErrorBody, ErrorResponse
from tts_common.schemas import Engine, IrodoriOptions, IrodoriVariant, PiperOptions, SynthesizeRequest

_LOGGER = logging.getLogger(__name__)


def _piper_headers(settings: Settings) -> dict[str, str]:
    return build_internal_headers(
        use_iam=settings.internal_use_iam,
        audience=settings.internal_iam_audience_piper or settings.piper_service_url,
    )


def _irodori_headers(settings: Settings) -> dict[str, str]:
    return build_internal_headers(
        use_iam=settings.internal_use_iam,
        audience=settings.internal_iam_audience_irodori or settings.irodori_service_url,
    )


async def route_synthesize(
    client: httpx.AsyncClient,
    settings: Settings,
    request: SynthesizeRequest,
    ref_audio: UploadFile | None = None,
) -> httpx.Response:
    if request.engine == Engine.PIPER:
        return await _call_piper(client, settings, request)
    return await _call_irodori(client, settings, request, ref_audio)


async def _call_piper(
    client: httpx.AsyncClient,
    settings: Settings,
    request: SynthesizeRequest,
) -> httpx.Response:
    opts = request.piper or PiperOptions()
    payload: dict[str, Any] = {
        "text": request.text,
        "speaker_id": opts.speaker_id,
        "length_scale": opts.length_scale,
        "noise_scale": opts.noise_scale,
        "noise_scale_w": opts.noise_scale_w,
        "language": opts.language,
    }
    try:
        response = await post_synthesize_json(
            client,
            settings.piper_service_url,
            payload,
            headers=_piper_headers(settings),
            timeout=settings.request_timeout,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="upstream_timeout",
                    message="Piper service timed out",
                    engine="piper",
                )
            ).model_dump(),
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="upstream_unreachable",
                    message=str(exc),
                    engine="piper",
                )
            ).model_dump(),
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "error": {
                    "code": "upstream_error",
                    "message": parse_error_response(response, "piper"),
                    "engine": "piper",
                }
            },
        )
    return response


async def _call_irodori(
    client: httpx.AsyncClient,
    settings: Settings,
    request: SynthesizeRequest,
    ref_audio: UploadFile | None,
) -> httpx.Response:
    opts = request.irodori or IrodoriOptions()
    data: dict[str, str] = {
        "text": request.text,
        "irodori_variant": opts.irodori_variant.value,
        "no_ref": "true" if opts.no_ref else "false",
        "num_steps": str(opts.num_steps),
        "cfg_scale_text": str(opts.cfg_scale_text),
        "cfg_scale_caption": str(opts.cfg_scale_caption),
        "cfg_scale_speaker": str(opts.cfg_scale_speaker),
    }
    if opts.caption is not None:
        data["caption"] = opts.caption
    if opts.seed is not None:
        data["seed"] = str(opts.seed)

    files = None
    if ref_audio is not None and ref_audio.filename:
        content = await ref_audio.read()
        files = {
            "ref_audio": (
                ref_audio.filename,
                content,
                ref_audio.content_type or "audio/wav",
            )
        }
        data["no_ref"] = "false"

    if opts.irodori_variant == IrodoriVariant.BASE and files is None and not opts.no_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="ref_audio_required",
                    message="ref_audio file or no_ref=true required for irodori base",
                    engine="irodori",
                )
            ).model_dump(),
        )

    try:
        response = await post_synthesize_multipart(
            client,
            settings.irodori_service_url,
            data,
            files,
            headers=_irodori_headers(settings),
            timeout=settings.request_timeout,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="upstream_timeout",
                    message="Irodori service timed out",
                    engine="irodori",
                )
            ).model_dump(),
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="upstream_unreachable",
                    message=str(exc),
                    engine="irodori",
                )
            ).model_dump(),
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "error": {
                    "code": "upstream_error",
                    "message": parse_error_response(response, "irodori"),
                    "engine": "irodori",
                }
            },
        )
    return response
