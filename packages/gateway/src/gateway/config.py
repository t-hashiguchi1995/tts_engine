from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_api_keys(raw: str) -> frozenset[str]:
    return frozenset(k.strip() for k in raw.split(",") if k.strip())


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    piper_service_url: str
    irodori_service_url: str
    internal_use_iam: bool
    internal_iam_audience_piper: str | None
    internal_iam_audience_irodori: str | None
    api_keys: frozenset[str]
    require_api_keys: bool
    request_timeout: float
    rate_limit_rpm: int
    max_upload_bytes: int
    allowed_origins: frozenset[str]

    @classmethod
    def from_env(cls) -> Settings:
        keys_raw = os.getenv("API_KEYS", "")
        origins_raw = os.getenv("ALLOWED_ORIGINS", "")
        max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "25"))
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
            piper_service_url=os.getenv("PIPER_SERVICE_URL", "http://piper:8080"),
            irodori_service_url=os.getenv(
                "IRODORI_SERVICE_URL", "http://irodori:8080"
            ),
            internal_use_iam=os.getenv("INTERNAL_USE_IAM", "false").lower()
            in ("1", "true", "yes"),
            internal_iam_audience_piper=os.getenv("INTERNAL_IAM_AUDIENCE_PIPER"),
            internal_iam_audience_irodori=os.getenv("INTERNAL_IAM_AUDIENCE_IRODORI"),
            api_keys=_parse_api_keys(keys_raw),
            require_api_keys=os.getenv("REQUIRE_API_KEYS", "false").lower()
            in ("1", "true", "yes"),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "600")),
            rate_limit_rpm=int(os.getenv("RATE_LIMIT_RPM", "0")),
            max_upload_bytes=max(1, max_upload_mb) * 1024 * 1024,
            allowed_origins=frozenset(
                o.strip() for o in origins_raw.split(",") if o.strip()
            ),
        )

    def validate_startup(self) -> None:
        if self.require_api_keys and not self.api_keys:
            raise RuntimeError(
                "REQUIRE_API_KEYS is enabled but API_KEYS is empty. "
                "Configure Secret Manager secret tts-api-keys or API_KEYS for local dev."
            )
