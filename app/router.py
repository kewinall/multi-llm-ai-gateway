import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from math import inf
from typing import Any

from app.config import Settings
from app.errors import GatewayError, ProviderRequestError
from app.governance import GovernanceStore
from app.models import ChatCompletionRequest
from app.observability import tracer
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
        governance: GovernanceStore | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.settings = settings
        self.state_backend = state_backend
        self.governance = governance or GovernanceStore(settings, state_backend)
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

    @staticmethod
    def _resolve(model_name: str, aliases: dict[str, str]) -> RouteTarget:
        canonical = aliases.get(model_name, model_name)
        if ":" not in canonical:
            raise ValueError(
                f"Model '{model_name}' must be an alias or use provider:model format"
            )
        provider, model = canonical.split(":", 1)
        if not provider or not model:
            raise ValueError(f"Invalid model target '{canonical}'")
        return RouteTarget(provider=provider, model=model, canonical=canonical)

    async def resolve(self, model_name: str) -> RouteTarget:
        snapshot = await self.governance.snapshot()
        return self._resolve(model_name, snapshot["aliases"])

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

    async def model_catalog(self) -> dict[str, Any]:
        snapshot = await self.governance.snapshot()
        return {
            **snapshot,
            "default_routing_policy": snapshot["routing_policy"],
        }

    def _dedupe_targets(
        self,
        candidates: list[str],
        aliases: dict[str, str],
    ) -> list[RouteTarget]:
        seen: set[str] = set()
        targets: list[RouteTarget] = []
        for candidate in candidates:
            target = self._resolve(candidate, aliases)
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

    @staticmethod
    def _cost_score(
        canonical_model: str,
        pricing: dict[str, dict[str, float]],
    ) -> float:
        price = pricing.get(canonical_model)
        if price is None:
            return inf
        return float(price.get("input_per_million", 0.0)) + float(
            price.get("output_per_million", 0.0)
        )

    async def candidates(
        self,
        request: ChatCompletionRequest,
    ) -> tuple[str, list[RouteTarget], dict[str, Any]]:
        snapshot = await self.governance.snapshot()
        configured_pool = snapshot["pools"].get(request.model)
        candidates = list(configured_pool) if configured_pool else [request.model]
        candidates.extend(self.settings.fallback_models)
        targets = self._dedupe_targets(candidates, snapshot["aliases"])

        policy = request.routing_policy or snapshot["routing_policy"]
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
                key=lambda target: self._cost_score(
                    target.canonical,
                    snapshot["pricing"],
                ),
            )
        else:
            raise ValueError(f"Unsupported routing policy '{policy}'")

        return policy, targets, snapshot

    async def stream_route(
        self,
        request: ChatCompletionRequest,
    ) -> tuple[AsyncIterator[dict[str, Any]], dict[str, Any]]:
        policy, targets, snapshot = await self.candidates(request)
        attempts: list[dict[str, Any]] = []

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
            if not provider.configured():
                attempts.append(
                    {
                        "target": target.canonical,
                        "retry": 0,
                        "status": "skipped",
                        "error": "provider_not_configured",
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

            attempts.append(
                {
                    "target": target.canonical,
                    "retry": 0,
                    "status": "stream_selected",
                }
            )
            metadata = {
                "provider": target.provider,
                "model": target.model,
                "requested_model": request.model,
                "routing_policy": policy,
                "candidate_order": [item.canonical for item in targets],
                "attempts": attempts,
                "fallback_used": target_index > 0,
                "state_backend": self.state_backend.name,
                "governance_distributed": snapshot["governance_distributed"],
                "stream": True,
            }

            async def wrapped_stream(
                selected_provider: BaseProvider = provider,
                selected_target: RouteTarget = target,
            ) -> AsyncIterator[dict[str, Any]]:
                try:
                    async for chunk in selected_provider.stream(
                        selected_target.model,
                        request,
                    ):
                        yield chunk
                    await self.circuit_breaker.success(selected_target.provider)
                except GatewayError:
                    await self.circuit_breaker.failure(selected_target.provider)
                    raise

            return wrapped_stream(), metadata

        summary = ", ".join(
            f"{attempt['target']}={attempt.get('error', attempt['status'])}"
            for attempt in attempts
        )
        raise ProviderRequestError(f"All streaming candidates failed: {summary}")

    async def route(
        self,
        request: ChatCompletionRequest,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        policy, targets, snapshot = await self.candidates(request)
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
                            "governance_distributed": snapshot[
                                "governance_distributed"
                            ],
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
