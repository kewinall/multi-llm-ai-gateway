from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"X-API-Key": "dev-gateway-key"}


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_providers_require_authentication() -> None:
    response = client.get("/v1/providers")
    assert response.status_code == 401


def test_provider_status() -> None:
    response = client.get("/v1/providers", headers=AUTH)
    assert response.status_code == 200
    providers = {item["name"]: item for item in response.json()["providers"]}
    assert providers["mock"]["configured"] is True


def test_mock_chat_completion() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "mock:demo",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "mock response: hello"
    assert body["gateway"]["provider"] == "mock"
    assert body["gateway"]["fallback_used"] is False


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


def test_streaming_is_rejected_in_v01() -> None:
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
