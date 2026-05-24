from __future__ import annotations

import json
import logging
from typing import Any

import httpx

_LOGGER = logging.getLogger(__name__)


def build_internal_headers(
    *,
    use_iam: bool,
    audience: str | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if not use_iam:
        return headers
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token
    except ImportError as exc:
        raise RuntimeError(
            "google-auth is required when INTERNAL_USE_IAM=true"
        ) from exc
    if not audience:
        raise ValueError("INTERNAL_IAM_AUDIENCE is required when INTERNAL_USE_IAM=true")
    request = google.auth.transport.requests.Request()
    token = google.oauth2.id_token.fetch_id_token(request, audience)
    headers["Authorization"] = f"Bearer {token}"
    return headers


async def post_synthesize_json(
    client: httpx.AsyncClient,
    base_url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 600.0,
) -> httpx.Response:
    url = f"{base_url.rstrip('/')}/internal/synthesize"
    return await client.post(
        url,
        json=payload,
        headers=headers,
        timeout=timeout,
    )


async def post_synthesize_multipart(
    client: httpx.AsyncClient,
    base_url: str,
    data: dict[str, str],
    files: dict[str, tuple[str, bytes, str]] | None,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 600.0,
) -> httpx.Response:
    url = f"{base_url.rstrip('/')}/internal/synthesize"
    return await client.post(
        url,
        data=data,
        files=files,
        headers=headers,
        timeout=timeout,
    )


async def fetch_health(
    client: httpx.AsyncClient,
    base_url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/health"
    response = await client.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def parse_error_response(response: httpx.Response, engine: str | None = None) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and "error" in body:
            err = body["error"]
            if isinstance(err, dict):
                return str(err.get("message", response.text))
        if isinstance(body, dict) and "detail" in body:
            detail = body["detail"]
            if isinstance(detail, list):
                return json.dumps(detail)
            return str(detail)
    except Exception:
        pass
    prefix = f"[{engine}] " if engine else ""
    return f"{prefix}upstream returned {response.status_code}"
