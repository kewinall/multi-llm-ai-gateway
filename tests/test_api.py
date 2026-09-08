import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app, state_backend

client = TestClient(app)
AUTH = {"X-API-Key": "dev-gateway-key"}


@pytest.fixture(autouse=True)
def reset_runtime_state() -> None:
    asyncio.run(state_backend.reset())


def test_health_and_readiness() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["version"] == "0.3.0"
    assert health.json()["state_backend"] == "memory"
    assert health.headers["X-Request-ID"]

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"ready": True, "state_backend": "memory"}


def test_providers_require_authentication() -> None:
    response = client.get("/v1/providers")
    assert response.status_code == 401


def test_provider_status_includes_circuit_state() -> None:
    response = client.get("/v1/providers", headers=AUTH)
    assert response.status_code == 200
    providers = {item["name"]: item for item in response.json()["providers"]}
    assert providers["mock"]["configured"] is True
    assert providers["mock"]["circuit"]["state"] == "closed"


def test_models_catalog_includes_state_backend() -> None:
    response = client.get("/v1/models", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["aliases"]["default"] == "mock:demo"
    assert body["pricing"]["mock:demo"]["input_per_million"] == 0.0
    assert body["state_backend"] == "memory"


def test_mock_chat_completion_records_usage_cost_and_backend() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "mock:demo",
            "messages": [{"role": "user", "content": "hello gateway"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "mock response: hello gateway"
    assert body["gateway"]["provider"] == "mock"
    assert body["gateway"]["routing_policy"] == "priority"
    assert body["gateway"]["cost_usd"] == 0.0
    assert body["gateway"]["pricing_known"] is True
    assert body["gateway"]["state_backend"] == "memory"
    assert response.headers["X-RateLimit-Limit"] == "60"

    usage = client.get("/v1/usage", headers=AUTH).json()
    assert usage["backend"] == "memory"
    assert usage["totals"]["requests"] == 1
    assert usage["totals"]["total_tokens"] > 0
    assert usage["by_model"]["mock:demo"]["requests"] == 1


def test_metrics_endpoint_exposes_gateway_metrics() -> None:
    client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "mock:demo",
            "messages": [{"role": "user", "content": "metrics"}],
        },
    )
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "llm_gateway_requests_total" in response.text
    assert "llm_gateway_tokens_total" in response.text


def test_budget_status_endpoint() -> None:
    response = client.get("/v1/budgets", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["daily"]["exhausted"] is False
    assert response.json()["monthly"]["exhausted"] is False


def test_streaming_is_rejected_in_v03() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "mock:demo",
            "stream": True,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 400
