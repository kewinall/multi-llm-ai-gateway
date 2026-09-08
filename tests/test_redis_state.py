import os
import uuid

import pytest

from app.state import RedisStateBackend


@pytest.mark.asyncio
async def test_redis_backend_shares_state_across_clients() -> None:
    url = os.getenv("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL is not configured")

    prefix = f"llm-gateway-test-{uuid.uuid4().hex}"
    first = RedisStateBackend(url, prefix)
    second = RedisStateBackend(url, prefix)

    try:
        await first.reset()
        assert await first.health() is True
        assert await second.health() is True

        rate1 = await first.rate_limit("principal", limit=2)
        rate2 = await second.rate_limit("principal", limit=2)
        rate3 = await first.rate_limit("principal", limit=2)
        assert rate1.allowed is True
        assert rate2.allowed is True
        assert rate3.allowed is False

        assert await first.round_robin_index("balanced", 2) == 0
        assert await second.round_robin_index("balanced", 2) == 1

        await first.usage_record(
            request_id="redis-1",
            provider="mock",
            model="demo",
            prompt_tokens=3,
            completion_tokens=4,
            cost_usd=0.25,
            pricing_known=True,
        )
        snapshot = await second.usage_snapshot()
        assert snapshot["backend"] == "redis"
        assert snapshot["totals"]["requests"] == 1
        assert snapshot["totals"]["total_tokens"] == 7
        assert snapshot["totals"]["cost_usd"] == 0.25

        await first.circuit_failure("provider", failure_threshold=1)
        status = await second.circuit_status("provider", recovery_seconds=60)
        assert status["state"] == "open"
        assert status["failures"] == 1

        await second.circuit_success("provider")
        assert (await first.circuit_status("provider", 60))["state"] == "closed"
    finally:
        await first.reset()
        await first.close()
        await second.close()
