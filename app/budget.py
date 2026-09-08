from typing import Any

from app.config import Settings
from app.usage import UsageStore


class BudgetManager:
    def __init__(self, settings: Settings, usage_store: UsageStore) -> None:
        self.settings = settings
        self.usage_store = usage_store

    @staticmethod
    def _period_status(spent: float, limit: float | None) -> dict[str, Any]:
        return {
            "spent_usd": round(spent, 8),
            "limit_usd": limit,
            "remaining_usd": None if limit is None else round(max(limit - spent, 0.0), 8),
            "exhausted": False if limit is None else spent >= limit,
        }

    async def status(self) -> dict[str, Any]:
        daily_spent = await self.usage_store.period_cost("day")
        monthly_spent = await self.usage_store.period_cost("month")
        return {
            "daily": self._period_status(daily_spent, self.settings.daily_budget_usd),
            "monthly": self._period_status(monthly_spent, self.settings.monthly_budget_usd),
        }

    async def allowed(self) -> bool:
        current = await self.status()
        return not current["daily"]["exhausted"] and not current["monthly"]["exhausted"]
