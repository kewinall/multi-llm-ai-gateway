from datetime import datetime
from typing import Any

from app.state import StateBackend, UsageRecord


class UsageStore:
    def __init__(self, backend: StateBackend) -> None:
        self.backend = backend

    async def record(
        self,
        *,
        request_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        pricing_known: bool,
        now: datetime | None = None,
    ) -> UsageRecord:
        return await self.backend.usage_record(
            request_id=request_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            pricing_known=pricing_known,
            now=now,
        )

    async def reset(self) -> None:
        await self.backend.reset()

    async def period_cost(self, period: str, now: datetime | None = None) -> float:
        return await self.backend.usage_period_cost(period, now)

    async def snapshot(self) -> dict[str, Any]:
        return await self.backend.usage_snapshot()
