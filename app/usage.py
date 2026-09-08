from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class UsageRecord:
    timestamp: str
    request_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    pricing_known: bool


class UsageStore:
    def __init__(self) -> None:
        self._records: list[UsageRecord] = []
        self._lock = Lock()

    def record(
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
        timestamp = now or datetime.now(UTC)
        item = UsageRecord(
            timestamp=timestamp.isoformat(),
            request_id=request_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
            pricing_known=pricing_known,
        )
        with self._lock:
            self._records.append(item)
        return item

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def period_cost(self, period: str, now: datetime | None = None) -> float:
        current = now or datetime.now(UTC)
        with self._lock:
            records = list(self._records)

        if period == "day":
            prefix = current.date().isoformat()
        elif period == "month":
            prefix = current.strftime("%Y-%m")
        else:
            raise ValueError("period must be 'day' or 'month'")

        return sum(record.cost_usd for record in records if record.timestamp.startswith(prefix))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            records = list(self._records)

        totals = {
            "requests": len(records),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        by_model: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }
        )

        for record in records:
            totals["prompt_tokens"] += record.prompt_tokens
            totals["completion_tokens"] += record.completion_tokens
            totals["total_tokens"] += record.total_tokens
            totals["cost_usd"] += record.cost_usd

            key = f"{record.provider}:{record.model}"
            row = by_model[key]
            row["requests"] += 1
            row["prompt_tokens"] += record.prompt_tokens
            row["completion_tokens"] += record.completion_tokens
            row["total_tokens"] += record.total_tokens
            row["cost_usd"] += record.cost_usd

        totals["cost_usd"] = round(float(totals["cost_usd"]), 8)
        for row in by_model.values():
            row["cost_usd"] = round(float(row["cost_usd"]), 8)

        return {
            "totals": totals,
            "by_model": dict(sorted(by_model.items())),
            "recent": [asdict(item) for item in records[-20:]],
        }
