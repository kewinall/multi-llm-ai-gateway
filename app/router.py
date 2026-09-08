from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.errors import ProviderRequestError
from app.models import ChatCompletionRequest
from app.providers import AnthropicProvider, GoogleProvider, MockProvider, OpenAIProvider
from app.providers.base import BaseProvider


@dataclass(frozen=True)
class RouteTarget:
    provider: str
    model: str
    canonical: str


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.providers: dict[str, BaseProvider] = {
            "openai": OpenAIProvider(settings),
            "anthropic": AnthropicProvider(settings),
            "google": GoogleProvider(settings),
            "mock": MockProvider(),
        }

    def resolve(self, model_name: str) -> RouteTarget:
        canonical = self.settings.model_aliases.get(model_name, model_name)
        if ":" not in canonical:
            raise ValueError(
                f"Model '{model_name}' must be an alias or use provider:model format"
            )
        provider, model = canonical.split(":", 1)
        if not provider or not model:
            raise ValueError(f"Invalid model target '{canonical}'")
        return RouteTarget(provider=provider, model=model, canonical=canonical)

    def provider_status(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "configured": provider.configured()}
            for name, provider in self.providers.items()
        ]

    async def route(
        self, request: ChatCompletionRequest
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        candidates = [request.model, *self.settings.fallback_models]
        seen: set[str] = set()
        attempts: list[dict[str, str]] = []

        for candidate in candidates:
            target = self.resolve(candidate)
            if target.canonical in seen:
                continue
            seen.add(target.canonical)

            provider = self.providers.get(target.provider)
            if provider is None:
                attempts.append(
                    {
                        "target": target.canonical,
                        "error": f"unknown provider '{target.provider}'",
                    }
                )
                continue

            try:
                result = await provider.chat(target.model, request)
                route_metadata = {
                    "provider": target.provider,
                    "model": target.model,
                    "requested_model": request.model,
                    "attempts": len(attempts) + 1,
                    "fallback_used": len(attempts) > 0,
                }
                return result, route_metadata
            except Exception as exc:
                attempts.append(
                    {
                        "target": target.canonical,
                        "error": type(exc).__name__,
                    }
                )

        summary = ", ".join(
            f"{attempt['target']}={attempt['error']}" for attempt in attempts
        )
        raise ProviderRequestError(f"All routing candidates failed: {summary}")
