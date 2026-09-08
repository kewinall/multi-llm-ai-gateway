import pytest

from app.config import Settings
from app.models import ChatCompletionRequest, ChatMessage
from app.router import ModelRouter


@pytest.mark.asyncio
async def test_fallback_to_mock_when_primary_is_not_configured() -> None:
    settings = Settings(
        gateway_api_key="",
        openai_api_key=None,
        provider_retry_attempts=1,
        model_aliases_json='{"primary":"openai:not-configured"}',
        fallback_models_json='["mock:demo"]',
    )
    router = ModelRouter(settings)
    request = ChatCompletionRequest(
        model="primary",
        messages=[ChatMessage(role="user", content="fallback")],
    )

    result, metadata = await router.route(request)

    assert result["choices"][0]["message"]["content"] == "mock response: fallback"
    assert metadata["provider"] == "mock"
    assert metadata["fallback_used"] is True
    assert len(metadata["attempts"]) == 3
    assert metadata["attempts"][-1]["status"] == "success"


@pytest.mark.asyncio
async def test_cost_policy_selects_cheapest_known_model() -> None:
    settings = Settings(
        gateway_api_key="",
        model_aliases_json="{}",
        model_pools_json='{"cheap":["mock:expensive","mock:cheap"]}',
        model_pricing_json=(
            '{"mock:expensive":{"input_per_million":5,"output_per_million":10},'
            '"mock:cheap":{"input_per_million":1,"output_per_million":2}}'
        ),
    )
    router = ModelRouter(settings)
    request = ChatCompletionRequest(
        model="cheap",
        routing_policy="cost",
        messages=[ChatMessage(role="user", content="choose")],
    )

    _result, metadata = await router.route(request)

    assert metadata["model"] == "cheap"
    assert metadata["candidate_order"] == ["mock:cheap", "mock:expensive"]


@pytest.mark.asyncio
async def test_round_robin_rotates_pool() -> None:
    settings = Settings(
        gateway_api_key="",
        model_aliases_json="{}",
        model_pools_json='{"balanced":["mock:a","mock:b"]}',
    )
    router = ModelRouter(settings)
    request = ChatCompletionRequest(
        model="balanced",
        routing_policy="round_robin",
        messages=[ChatMessage(role="user", content="rotate")],
    )

    _first_result, first = await router.route(request)
    _second_result, second = await router.route(request)

    assert first["candidate_order"] == ["mock:a", "mock:b"]
    assert second["candidate_order"] == ["mock:b", "mock:a"]
    assert first["model"] == "a"
    assert second["model"] == "b"


def test_resolve_requires_provider_prefix_or_alias() -> None:
    router = ModelRouter(Settings(model_aliases_json="{}"))

    with pytest.raises(ValueError):
        router.resolve("missing-prefix")
