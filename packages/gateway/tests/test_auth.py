from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from gateway.config import Settings
from gateway.main import create_app


@pytest.fixture
def secured_client() -> TestClient:
    settings = Settings(
        host="127.0.0.1",
        port=8080,
        piper_service_url="http://piper:8080",
        irodori_service_url="http://irodori:8080",
        internal_use_iam=False,
        internal_iam_audience_piper=None,
        internal_iam_audience_irodori=None,
        api_keys=frozenset({"test-secret-key"}),
        require_api_keys=True,
        request_timeout=30.0,
        rate_limit_rpm=0,
        max_upload_bytes=25 * 1024 * 1024,
        allowed_origins=frozenset(),
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_health_is_public(secured_client: TestClient) -> None:
    # Health is used by load balancers; backends may be unreachable in unit tests.
    response = secured_client.get("/health")
    assert response.status_code == 200


def test_engines_requires_api_key(secured_client: TestClient) -> None:
    assert secured_client.get("/v1/engines").status_code == 401
    assert (
        secured_client.get(
            "/v1/engines",
            headers={"Authorization": "Bearer test-secret-key"},
        ).status_code
        == 200
    )


def test_invalid_api_key_rejected(secured_client: TestClient) -> None:
    response = secured_client.get(
        "/v1/engines",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401
