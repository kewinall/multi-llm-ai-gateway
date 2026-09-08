import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app, governance, state_backend

client = TestClient(app)
ADMIN = {"X-Admin-Key": "dev-admin-key"}
BOOTSTRAP = {"X-API-Key": "dev-gateway-key"}


@pytest.fixture(autouse=True)
def reset_runtime_state() -> None:
    asyncio.run(state_backend.reset())
    asyncio.run(governance.reset())


def create_client(role: str, name: str = "test-client", rpm: int | None = None) -> dict:
    payload = {"name": name, "role": role}
    if rpm is not None:
        payload["rate_limit_requests_per_minute"] = rpm
    response = client.post("/admin/api/clients", headers=ADMIN, json=payload)
    assert response.status_code == 201
    return response.json()


def test_admin_console_is_served() -> None:
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Multi-LLM AI Gateway" in response.text
    assert "API Clients / RBAC" in response.text


def test_admin_api_requires_admin_credential() -> None:
    assert client.get("/admin/api/summary").status_code == 401
    assert client.get("/admin/api/summary", headers=BOOTSTRAP).status_code == 403
    assert client.get("/admin/api/summary", headers=ADMIN).status_code == 200


def test_dynamic_alias_is_immediately_used_by_router() -> None:
    updated = client.put(
        "/admin/api/aliases/managed",
        headers=ADMIN,
        json={"target": "mock:dynamic"},
    )
    assert updated.status_code == 200

    models = client.get("/v1/models", headers=BOOTSTRAP).json()
    assert models["aliases"]["managed"] == "mock:dynamic"

    response = client.post(
        "/v1/chat/completions",
        headers=BOOTSTRAP,
        json={
            "model": "managed",
            "messages": [{"role": "user", "content": "dynamic routing"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["gateway"]["model"] == "dynamic"


def test_dynamic_pool_policy_and_pricing_are_governed_without_restart() -> None:
    assert client.put(
        "/admin/api/pools/managed-pool",
        headers=ADMIN,
        json={"models": ["mock:expensive", "mock:cheap"]},
    ).status_code == 200
    assert client.put(
        "/admin/api/pricing/mock:expensive",
        headers=ADMIN,
        json={"input_per_million": 8, "output_per_million": 16},
    ).status_code == 200
    assert client.put(
        "/admin/api/pricing/mock:cheap",
        headers=ADMIN,
        json={"input_per_million": 1, "output_per_million": 2},
    ).status_code == 200
    assert client.put(
        "/admin/api/settings/routing-policy",
        headers=ADMIN,
        json={"routing_policy": "cost"},
    ).status_code == 200

    response = client.post(
        "/v1/chat/completions",
        headers=BOOTSTRAP,
        json={
            "model": "managed-pool",
            "messages": [{"role": "user", "content": "pick cheap"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gateway"]["model"] == "cheap"
    assert body["gateway"]["routing_policy"] == "cost"
    assert body["gateway"]["pricing_known"] is True
    assert body["gateway"]["cost_usd"] > 0


def test_managed_client_key_is_shown_once_and_hash_backed() -> None:
    created = create_client("operator", "rag-service", rpm=7)
    assert created["api_key"].startswith("llmgw_")
    api_key = created["api_key"]

    listed = client.get("/admin/api/clients", headers=ADMIN).json()["clients"]
    assert len(listed) == 1
    assert listed[0]["name"] == "rag-service"
    assert "api_key" not in listed[0]

    response = client.post(
        "/v1/chat/completions",
        headers={"X-API-Key": api_key},
        json={
            "model": "mock:demo",
            "messages": [{"role": "user", "content": "managed client"}],
        },
    )
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "7"
    assert response.json()["gateway"]["client"]["name"] == "rag-service"


def test_viewer_can_read_but_cannot_call_model() -> None:
    viewer = create_client("viewer", "auditor")
    headers = {"X-API-Key": viewer["api_key"]}

    assert client.get("/v1/models", headers=headers).status_code == 200
    response = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "mock:demo",
            "messages": [{"role": "user", "content": "blocked"}],
        },
    )
    assert response.status_code == 403


def test_managed_admin_can_use_admin_api() -> None:
    managed_admin = create_client("admin", "platform-admin")
    headers = {"X-API-Key": managed_admin["api_key"]}
    response = client.get("/admin/api/summary", headers=headers)
    assert response.status_code == 200
    assert response.json()["actor"]["role"] == "admin"


def test_disabled_client_is_rejected_and_audit_is_recorded() -> None:
    created = create_client("operator", "disable-me")
    client_id = created["id"]
    api_key = created["api_key"]

    response = client.patch(
        f"/admin/api/clients/{client_id}",
        headers=ADMIN,
        json={"enabled": False},
    )
    assert response.status_code == 200

    denied = client.get("/v1/models", headers={"X-API-Key": api_key})
    assert denied.status_code == 401

    audit = client.get("/admin/api/audit", headers=ADMIN).json()["events"]
    resources = {event["resource"] for event in audit}
    assert f"client:{client_id}" in resources


def test_policy_can_deny_streaming_for_operator() -> None:
    policy = client.put(
        "/admin/api/policies/no-stream",
        headers=ADMIN,
        json={
            "priority": 10,
            "effect": "allow",
            "roles": ["operator"],
            "models": ["mock:*"],
            "allow_stream": False,
        },
    )
    assert policy.status_code == 200

    denied = client.post(
        "/v1/chat/completions",
        headers=BOOTSTRAP,
        json={
            "model": "mock:demo",
            "stream": True,
            "messages": [{"role": "user", "content": "policy"}],
        },
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["policy"] == "no-stream"
    assert denied.json()["detail"]["reason"] == "streaming_denied"


def test_explicit_deny_policy_blocks_matching_model() -> None:
    assert client.put(
        "/admin/api/policies/block-secret-model",
        headers=ADMIN,
        json={
            "priority": 1,
            "effect": "deny",
            "models": ["mock:secret*"],
        },
    ).status_code == 200

    denied = client.post(
        "/v1/chat/completions",
        headers=BOOTSTRAP,
        json={
            "model": "mock:secret-v1",
            "messages": [{"role": "user", "content": "blocked"}],
        },
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["reason"] == "explicit_deny"


def test_client_key_rotation_invalidates_old_key() -> None:
    created = create_client("operator", "rotate-me")
    old_key = created["api_key"]

    rotated = client.post(
        f"/admin/api/clients/{created['id']}/rotate-key",
        headers=ADMIN,
    )
    assert rotated.status_code == 200
    new_key = rotated.json()["api_key"]
    assert new_key.startswith("llmgw_")
    assert new_key != old_key

    assert client.get("/v1/models", headers={"X-API-Key": old_key}).status_code == 401
    assert client.get("/v1/models", headers={"X-API-Key": new_key}).status_code == 200

    audit = client.get("/admin/api/audit", headers=ADMIN).json()["events"]
    assert any(event["action"] == "rotate_key" for event in audit)
