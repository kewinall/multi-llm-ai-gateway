from datetime import UTC, datetime

import pytest

from app.budget import BudgetManager
from app.config import Settings
from app.rate_limit import RateLimiter
from app.resilience import CircuitBreaker
from app.state import InMemoryStateBackend
from app.usage import UsageStore


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit() -> None:
    backend = InMemoryStateBackend()
    limiter = RateLimiter(backend, 2)

    first = await limiter.check("client")
    second = await limiter.check("client")
    third = await limiter.check("client")

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.remaining == 0


@pytest.mark.asyncio
async def test_budget_manager_detects_exhausted_daily_budget() -> None:
    settings = Settings(daily_budget_usd=1.0, monthly_budget_usd=10.0)
    backend = InMemoryStateBackend()
    store = UsageStore(backend)
    await store.record(
        request_id="req-1",
        provider="mock",
        model="paid",
        prompt_tokens=100,
        completion_tokens=100,
        cost_usd=1.25,
        pricing_known=True,
        now=datetime.now(UTC),
    )
    manager = BudgetManager(settings, store)

    status = await manager.status()

    assert status["daily"]["exhausted"] is True
    assert status["monthly"]["exhausted"] is False
    assert await manager.allowed() is False


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_resets() -> None:
    backend = InMemoryStateBackend()
    breaker = CircuitBreaker(
        backend,
        failure_threshold=2,
        recovery_seconds=60,
    )

    await breaker.failure("provider")
    assert await breaker.allow("provider") is True

    await breaker.failure("provider")
    assert await breaker.allow("provider") is False
    assert (await breaker.status("provider"))["state"] == "open"

    assert (await backend.circuit_status("provider", 0))["state"] == "half_open"

    await breaker.success("provider")
    assert (await breaker.status("provider"))["state"] == "closed"
