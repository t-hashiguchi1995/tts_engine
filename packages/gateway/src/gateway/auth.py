from __future__ import annotations

import hmac

from fastapi import HTTPException, status

from gateway.config import Settings
from tts_common.errors import ErrorBody, ErrorResponse


def _constant_time_key_match(token: str, allowed: frozenset[str]) -> bool:
    for candidate in allowed:
        if hmac.compare_digest(token, candidate):
            return True
    return False


def verify_api_key(settings: Settings, authorization: str | None) -> None:
    if not settings.api_keys:
        if settings.require_api_keys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ErrorResponse(
                    error=ErrorBody(
                        code="misconfigured",
                        message="API key authentication is required but no keys are configured",
                    )
                ).model_dump(),
            )
        return

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error=ErrorBody(code="unauthorized", message="Missing Authorization header")
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error=ErrorBody(code="unauthorized", message="Invalid Authorization scheme")
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _constant_time_key_match(token, settings.api_keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error=ErrorBody(code="unauthorized", message="Invalid API key")
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )
