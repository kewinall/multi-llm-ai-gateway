import pytest

from app.config import Settings
from app.models import ChatCompletionRequest, ChatMessage
from app.router import ModelRouter


@pytest.mark.asyncio
async def test_fallback_to_mock_when_primary_is_not_configured() -> None:
    settings = Settings(
        gateway_api_key="",
        openai_api_key=None,
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
    assert metadata["attempts"] == 2


def test_resolve_requires_provider_prefix_or_alias() -> None:
    router = ModelRouter(Settings(model_aliases_json="{}"))

    with pytest.raises(ValueError):
        router.resolve("missing-prefix")
