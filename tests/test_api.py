import pytest
from fastapi.testclient import TestClient

from app.main import app, circuit_breaker, rate_limiter, usage_store

client = TestClient(app)
AUTH = {"X-API-Key": "dev-gateway-key"}


@pytest.fixture(autouse=True)
def reset_runtime_state() -> None:
    usage_store.reset()
    rate_limiter.reset()
    circuit_breaker.reset()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.2.0"}
    assert response.headers["X-Request-ID"]


def test_providers_require_authentication() -> None:
    response = client.get("/v1/providers")
    assert response.status_code == 401


def test_provider_status_includes_circuit_state() -> None:
    response = client.get("/v1/providers", headers=AUTH)
    assert response.status_code == 200
    providers = {item["name"]: item for item in response.json()["providers"]}
    assert providers["mock"]["configured"] is True
    assert providers["mock"]["circuit"]["state"] == "closed"


def test_models_catalog() -> None:
    response = client.get("/v1/models", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["aliases"]["default"] == "mock:demo"
    assert body["pricing"]["mock:demo"]["input_per_million"] == 0.0


def test_mock_chat_completion_records_usage_and_cost() -> None:
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
    assert response.headers["X-RateLimit-Limit"] == "60"

    usage = client.get("/v1/usage", headers=AUTH).json()
    assert usage["totals"]["requests"] == 1
    assert usage["totals"]["total_tokens"] > 0
    assert usage["by_model"]["mock:demo"]["requests"] == 1


def test_default_model_alias() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "default",
            "messages": [{"role": "user", "content": "alias"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["gateway"]["model"] == "demo"


def test_budget_status_endpoint() -> None:
    response = client.get("/v1/budgets", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["daily"]["exhausted"] is False
    assert response.json()["monthly"]["exhausted"] is False


def test_streaming_is_rejected_in_v02() -> None:
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
