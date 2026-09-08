from datetime import UTC, datetime

from app.budget import BudgetManager
from app.config import Settings
from app.rate_limit import RateLimiter
from app.resilience import CircuitBreaker
from app.usage import UsageStore


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = RateLimiter(2)

    first = limiter.check("client", now=100.0)
    second = limiter.check("client", now=101.0)
    third = limiter.check("client", now=102.0)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.remaining == 0


def test_budget_manager_detects_exhausted_daily_budget() -> None:
    settings = Settings(daily_budget_usd=1.0, monthly_budget_usd=10.0)
    store = UsageStore()
    store.record(
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

    status = manager.status()

    assert status["daily"]["exhausted"] is True
    assert status["monthly"]["exhausted"] is False
    assert manager.allowed() is False


def test_circuit_breaker_opens_and_recovers() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=30)

    breaker.failure("provider", now=100.0)
    assert breaker.allow("provider", now=101.0) is True

    breaker.failure("provider", now=102.0)
    assert breaker.allow("provider", now=103.0) is False
    assert breaker.status("provider", now=103.0)["state"] == "open"

    assert breaker.allow("provider", now=133.0) is True
    assert breaker.status("provider", now=133.0)["state"] == "half_open"

    breaker.success("provider")
    assert breaker.status("provider", now=134.0)["state"] == "closed"
