import random
from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.config import Settings
from app.errors import GatewayError, ProviderRequestError
from app.models import ChatCompletionRequest
from app.pricing import PricingCatalog
from app.providers import AnthropicProvider, GoogleProvider, MockProvider, OpenAIProvider
from app.providers.base import BaseProvider
from app.resilience import CircuitBreaker


@dataclass(frozen=True)
class RouteTarget:
    provider: str
    model: str
    canonical: str


class ModelRouter:
    def __init__(
        self,
        settings: Settings,
        pricing: PricingCatalog | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.settings = settings
        self.pricing = pricing or PricingCatalog(settings)
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=settings.circuit_failure_threshold,
            recovery_seconds=settings.circuit_recovery_seconds,
        )
        self.providers: dict[str, BaseProvider] = {
            "openai": OpenAIProvider(settings),
            "anthropic": AnthropicProvider(settings),
            "google": GoogleProvider(settings),
            "mock": MockProvider(),
        }
        self._round_robin_cursors: dict[str, int] = {}
        self._round_robin_lock = Lock()

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
            {
                "name": name,
                "configured": provider.configured(),
                "circuit": self.circuit_breaker.status(name),
            }
            for name, provider in self.providers.items()
        ]

    def model_catalog(self) -> dict[str, Any]:
        return {
            "aliases": self.settings.model_aliases,
            "pools": self.settings.model_pools,
            "pricing": self.pricing.as_dict(),
            "default_routing_policy": self.settings.routing_policy,
        }

    def _dedupe_targets(self, candidates: list[str]) -> list[RouteTarget]:
        seen: set[str] = set()
        targets: list[RouteTarget] = []
        for candidate in candidates:
            target = self.resolve(candidate)
            if target.canonical in seen:
                continue
            seen.add(target.canonical)
            targets.append(target)
        return targets

    def _round_robin(self, key: str, targets: list[RouteTarget]) -> list[RouteTarget]:
        if len(targets) < 2:
            return targets
        with self._round_robin_lock:
            cursor = self._round_robin_cursors.get(key, 0) % len(targets)
            self._round_robin_cursors[key] = cursor + 1
        return targets[cursor:] + targets[:cursor]

    def candidates(self, request: ChatCompletionRequest) -> tuple[str, list[RouteTarget]]:
        configured_pool = self.settings.model_pools.get(request.model)
        candidates = list(configured_pool) if configured_pool else [request.model]
        candidates.extend(self.settings.fallback_models)
        targets = self._dedupe_targets(candidates)

        policy = request.routing_policy or self.settings.routing_policy
        if policy == "priority":
            pass
        elif policy == "round_robin":
            targets = self._round_robin(request.model, targets)
        elif policy == "random":
            targets = list(targets)
            random.shuffle(targets)
        elif policy == "cost":
            targets = sorted(
                targets,
                key=lambda target: self.pricing.routing_cost_score(target.canonical),
            )
        else:
            raise ValueError(f"Unsupported routing policy '{policy}'")

        return policy, targets

    async def route(
        self, request: ChatCompletionRequest
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        policy, targets = self.candidates(request)
        attempts: list[dict[str, Any]] = []
        retry_limit = max(self.settings.provider_retry_attempts, 0)

        for target_index, target in enumerate(targets):
            provider = self.providers.get(target.provider)
            if provider is None:
                attempts.append(
                    {
                        "target": target.canonical,
                        "retry": 0,
                        "status": "skipped",
                        "error": f"unknown provider '{target.provider}'",
                    }
                )
                continue

            if not self.circuit_breaker.allow(target.provider):
                attempts.append(
                    {
                        "target": target.canonical,
                        "retry": 0,
                        "status": "skipped",
                        "error": "circuit_open",
                    }
                )
                continue

            for retry in range(retry_limit + 1):
                try:
                    result = await provider.chat(target.model, request)
                    self.circuit_breaker.success(target.provider)
                    attempts.append(
                        {
                            "target": target.canonical,
                            "retry": retry,
                            "status": "success",
                        }
                    )
                    route_metadata = {
                        "provider": target.provider,
                        "model": target.model,
                        "requested_model": request.model,
                        "routing_policy": policy,
                        "candidate_order": [item.canonical for item in targets],
                        "attempts": attempts,
                        "fallback_used": target_index > 0,
                    }
                    return result, route_metadata
                except GatewayError as exc:
                    self.circuit_breaker.failure(target.provider)
                    attempts.append(
                        {
                            "target": target.canonical,
                            "retry": retry,
                            "status": "failed",
                            "error": type(exc).__name__,
                        }
                    )

        summary = ", ".join(
            f"{attempt['target']}={attempt.get('error', attempt['status'])}"
            for attempt in attempts
        )
        raise ProviderRequestError(f"All routing candidates failed: {summary}")
