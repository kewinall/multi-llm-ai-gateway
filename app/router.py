import random
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.errors import GatewayError, ProviderRequestError
from app.models import ChatCompletionRequest
from app.observability import tracer
from app.pricing import PricingCatalog
from app.providers import AnthropicProvider, GoogleProvider, MockProvider, OpenAIProvider
from app.providers.base import BaseProvider
from app.resilience import CircuitBreaker
from app.state import StateBackend


@dataclass(frozen=True)
class RouteTarget:
    provider: str
    model: str
    canonical: str


class ModelRouter:
    def __init__(
        self,
        settings: Settings,
        state_backend: StateBackend,
        pricing: PricingCatalog | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.settings = settings
        self.state_backend = state_backend
        self.pricing = pricing or PricingCatalog(settings)
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            state_backend,
            failure_threshold=settings.circuit_failure_threshold,
            recovery_seconds=settings.circuit_recovery_seconds,
        )
        self.providers: dict[str, BaseProvider] = {
            "openai": OpenAIProvider(settings),
            "anthropic": AnthropicProvider(settings),
            "google": GoogleProvider(settings),
            "mock": MockProvider(),
        }
        self._tracer = tracer(__name__)

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

    async def provider_status(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name, provider in self.providers.items():
            rows.append(
                {
                    "name": name,
                    "configured": provider.configured(),
                    "circuit": await self.circuit_breaker.status(name),
                }
            )
        return rows

    def model_catalog(self) -> dict[str, Any]:
        return {
            "aliases": self.settings.model_aliases,
            "pools": self.settings.model_pools,
            "pricing": self.pricing.as_dict(),
            "default_routing_policy": self.settings.routing_policy,
            "state_backend": self.state_backend.name,
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

    async def _round_robin(
        self,
        key: str,
        targets: list[RouteTarget],
    ) -> list[RouteTarget]:
        if len(targets) < 2:
            return targets
        cursor = await self.state_backend.round_robin_index(key, len(targets))
        return targets[cursor:] + targets[:cursor]

    async def candidates(
        self,
        request: ChatCompletionRequest,
    ) -> tuple[str, list[RouteTarget]]:
        configured_pool = self.settings.model_pools.get(request.model)
        candidates = list(configured_pool) if configured_pool else [request.model]
        candidates.extend(self.settings.fallback_models)
        targets = self._dedupe_targets(candidates)

        policy = request.routing_policy or self.settings.routing_policy
        if policy == "priority":
            pass
        elif policy == "round_robin":
            targets = await self._round_robin(request.model, targets)
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
        self,
        request: ChatCompletionRequest,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        policy, targets = await self.candidates(request)
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

            if not await self.circuit_breaker.allow(target.provider):
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
                with self._tracer.start_as_current_span("llm.provider.request") as span:
                    span.set_attribute("llm.provider", target.provider)
                    span.set_attribute("llm.model", target.model)
                    span.set_attribute("llm.routing.policy", policy)
                    span.set_attribute("llm.retry", retry)
                    try:
                        result = await provider.chat(target.model, request)
                        await self.circuit_breaker.success(target.provider)
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
                            "state_backend": self.state_backend.name,
                        }
                        return result, route_metadata
                    except GatewayError as exc:
                        span.record_exception(exc)
                        await self.circuit_breaker.failure(target.provider)
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
