import hashlib
import json
import math
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import Settings


@dataclass(frozen=True)
class RateLimitState:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


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


class StateBackend(ABC):
    name: str

    @abstractmethod
    async def health(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rate_limit(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitState:
        raise NotImplementedError

    @abstractmethod
    async def round_robin_index(self, key: str, size: int) -> int:
        raise NotImplementedError

    @abstractmethod
    async def circuit_allow(self, provider: str, recovery_seconds: float) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def circuit_success(self, provider: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def circuit_failure(self, provider: str, failure_threshold: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def circuit_status(
        self,
        provider: str,
        recovery_seconds: float,
    ) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    async def usage_record(
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
        raise NotImplementedError

    @abstractmethod
    async def usage_period_cost(
        self,
        period: str,
        now: datetime | None = None,
    ) -> float:
        raise NotImplementedError

    @abstractmethod
    async def usage_snapshot(self) -> dict[str, Any]:
        raise NotImplementedError

    async def close(self) -> None:
        return None


class InMemoryStateBackend(StateBackend):
    name = "memory"

    def __init__(self) -> None:
        self._rate_requests: dict[str, deque[float]] = defaultdict(deque)
        self._round_robin: dict[str, int] = {}
        self._circuits: dict[str, dict[str, float | int | None]] = {}
        self._records: list[UsageRecord] = []
        self._lock = Lock()

    async def health(self) -> bool:
        return True

    async def reset(self) -> None:
        with self._lock:
            self._rate_requests.clear()
            self._round_robin.clear()
            self._circuits.clear()
            self._records.clear()

    async def rate_limit(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitState:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._rate_requests[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, math.ceil(bucket[0] + window_seconds - now))
                return RateLimitState(False, limit, 0, retry_after)

            bucket.append(now)
            remaining = max(limit - len(bucket), 0)
        return RateLimitState(True, limit, remaining, 0)

    async def round_robin_index(self, key: str, size: int) -> int:
        if size <= 0:
            raise ValueError("size must be positive")
        with self._lock:
            cursor = self._round_robin.get(key, 0)
            self._round_robin[key] = cursor + 1
        return cursor % size

    async def circuit_allow(self, provider: str, recovery_seconds: float) -> bool:
        now = time.time()
        with self._lock:
            state = self._circuits.get(provider)
            if not state or state.get("opened_at") is None:
                return True
            opened_at = float(state["opened_at"])
        return now - opened_at >= recovery_seconds

    async def circuit_success(self, provider: str) -> None:
        with self._lock:
            self._circuits.pop(provider, None)

    async def circuit_failure(self, provider: str, failure_threshold: int) -> None:
        now = time.time()
        with self._lock:
            state = self._circuits.setdefault(
                provider,
                {"failures": 0, "opened_at": None},
            )
            failures = int(state["failures"]) + 1
            state["failures"] = failures
            if failures >= failure_threshold:
                state["opened_at"] = now

    async def circuit_status(
        self,
        provider: str,
        recovery_seconds: float,
    ) -> dict[str, object]:
        now = time.time()
        with self._lock:
            state = self._circuits.get(
                provider,
                {"failures": 0, "opened_at": None},
            ).copy()

        opened_at = state.get("opened_at")
        if opened_at is None:
            name = "closed"
        elif now - float(opened_at) >= recovery_seconds:
            name = "half_open"
        else:
            name = "open"
        return {"state": name, "failures": int(state["failures"])}

    async def usage_record(
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

    async def usage_period_cost(
        self,
        period: str,
        now: datetime | None = None,
    ) -> float:
        current = now or datetime.now(UTC)
        if period == "day":
            prefix = current.date().isoformat()
        elif period == "month":
            prefix = current.strftime("%Y-%m")
        else:
            raise ValueError("period must be 'day' or 'month'")

        with self._lock:
            return sum(
                record.cost_usd
                for record in self._records
                if record.timestamp.startswith(prefix)
            )

    async def usage_snapshot(self) -> dict[str, Any]:
        with self._lock:
            records = list(self._records)

        totals: dict[str, int | float] = {
            "requests": len(records),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        by_model: dict[str, dict[str, int | float]] = defaultdict(
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

            canonical = f"{record.provider}:{record.model}"
            row = by_model[canonical]
            row["requests"] += 1
            row["prompt_tokens"] += record.prompt_tokens
            row["completion_tokens"] += record.completion_tokens
            row["total_tokens"] += record.total_tokens
            row["cost_usd"] += record.cost_usd

        totals["cost_usd"] = round(float(totals["cost_usd"]), 8)
        for row in by_model.values():
            row["cost_usd"] = round(float(row["cost_usd"]), 8)

        return {
            "backend": self.name,
            "totals": totals,
            "by_model": dict(sorted(by_model.items())),
            "recent": [asdict(item) for item in records[-20:]],
        }


class RedisStateBackend(StateBackend):
    name = "redis"

    _RATE_LIMIT_SCRIPT = """
    redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[2])
    local count = redis.call('ZCARD', KEYS[1])
    if count >= tonumber(ARGV[3]) then
      local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
      return {0, count, oldest[2] or ARGV[1]}
    end
    redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[5]) + 1)
    return {1, count + 1, 0}
    """

    _CIRCUIT_FAILURE_SCRIPT = """
    local failures = redis.call('HINCRBY', KEYS[1], 'failures', 1)
    if failures >= tonumber(ARGV[1]) then
      redis.call('HSET', KEYS[1], 'opened_at', ARGV[2])
    end
    return failures
    """

    def __init__(self, url: str, prefix: str = "llm-gateway") -> None:
        self.redis = redis.from_url(url, decode_responses=True)
        self.prefix = prefix.rstrip(":")

    def _key(self, *parts: str) -> str:
        return ":".join([self.prefix, *parts])

    async def health(self) -> bool:
        try:
            return bool(await self.redis.ping())
        except RedisError:
            return False

    async def reset(self) -> None:
        keys = [key async for key in self.redis.scan_iter(match=f"{self.prefix}:*")]
        if keys:
            await self.redis.delete(*keys)

    async def rate_limit(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitState:
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - window_seconds * 1000
        redis_key = self._key("rate", key)
        member = f"{now_ms}:{uuid.uuid4().hex}"
        result = await self.redis.eval(
            self._RATE_LIMIT_SCRIPT,
            1,
            redis_key,
            now_ms,
            cutoff_ms,
            limit,
            member,
            window_seconds,
        )
        allowed = bool(int(result[0]))
        count = int(result[1])

        retry_after = 0
        if not allowed:
            oldest_ms = float(result[2])
            retry_after = max(
                1,
                math.ceil((oldest_ms + window_seconds * 1000 - now_ms) / 1000),
            )

        return RateLimitState(
            allowed=allowed,
            limit=limit,
            remaining=max(limit - count, 0) if allowed else 0,
            retry_after_seconds=retry_after,
        )

    async def round_robin_index(self, key: str, size: int) -> int:
        if size <= 0:
            raise ValueError("size must be positive")
        value = await self.redis.incr(self._key("round-robin", key))
        return (int(value) - 1) % size

    async def circuit_allow(self, provider: str, recovery_seconds: float) -> bool:
        state = await self.redis.hgetall(self._key("circuit", provider))
        opened_at = state.get("opened_at")
        if opened_at is None:
            return True
        return time.time() - float(opened_at) >= recovery_seconds

    async def circuit_success(self, provider: str) -> None:
        await self.redis.delete(self._key("circuit", provider))

    async def circuit_failure(self, provider: str, failure_threshold: int) -> None:
        await self.redis.eval(
            self._CIRCUIT_FAILURE_SCRIPT,
            1,
            self._key("circuit", provider),
            failure_threshold,
            time.time(),
        )

    async def circuit_status(
        self,
        provider: str,
        recovery_seconds: float,
    ) -> dict[str, object]:
        state = await self.redis.hgetall(self._key("circuit", provider))
        failures = int(state.get("failures", 0))
        opened_at = state.get("opened_at")

        if opened_at is None:
            name = "closed"
        elif time.time() - float(opened_at) >= recovery_seconds:
            name = "half_open"
        else:
            name = "open"
        return {"state": name, "failures": failures}

    async def usage_record(
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
        canonical = f"{provider}:{model}"
        totals_key = self._key("usage", "totals")
        model_key = self._key("usage", "model", canonical)
        models_key = self._key("usage", "models")
        day_key = self._key("usage", "cost", "day", timestamp.date().isoformat())
        month_key = self._key("usage", "cost", "month", timestamp.strftime("%Y-%m"))
        recent_key = self._key("usage", "recent")

        pipe = self.redis.pipeline(transaction=True)
        for key in (totals_key, model_key):
            pipe.hincrby(key, "requests", 1)
            pipe.hincrby(key, "prompt_tokens", prompt_tokens)
            pipe.hincrby(key, "completion_tokens", completion_tokens)
            pipe.hincrby(key, "total_tokens", item.total_tokens)
            pipe.hincrbyfloat(key, "cost_usd", cost_usd)
        pipe.sadd(models_key, canonical)
        pipe.incrbyfloat(day_key, cost_usd)
        pipe.incrbyfloat(month_key, cost_usd)
        pipe.lpush(recent_key, json.dumps(asdict(item), separators=(",", ":")))
        pipe.ltrim(recent_key, 0, 19)
        await pipe.execute()
        return item

    async def usage_period_cost(
        self,
        period: str,
        now: datetime | None = None,
    ) -> float:
        current = now or datetime.now(UTC)
        if period == "day":
            suffix = current.date().isoformat()
        elif period == "month":
            suffix = current.strftime("%Y-%m")
        else:
            raise ValueError("period must be 'day' or 'month'")
        value = await self.redis.get(self._key("usage", "cost", period, suffix))
        return float(value or 0.0)

    @staticmethod
    def _usage_hash(raw: dict[str, str]) -> dict[str, int | float]:
        return {
            "requests": int(raw.get("requests", 0)),
            "prompt_tokens": int(raw.get("prompt_tokens", 0)),
            "completion_tokens": int(raw.get("completion_tokens", 0)),
            "total_tokens": int(raw.get("total_tokens", 0)),
            "cost_usd": round(float(raw.get("cost_usd", 0.0)), 8),
        }

    async def usage_snapshot(self) -> dict[str, Any]:
        totals = self._usage_hash(
            await self.redis.hgetall(self._key("usage", "totals"))
        )
        models = sorted(await self.redis.smembers(self._key("usage", "models")))
        by_model: dict[str, dict[str, int | float]] = {}
        if models:
            pipe = self.redis.pipeline(transaction=False)
            for model in models:
                pipe.hgetall(self._key("usage", "model", model))
            model_rows = await pipe.execute()
            by_model = {
                model: self._usage_hash(row)
                for model, row in zip(models, model_rows, strict=True)
            }

        raw_recent = await self.redis.lrange(self._key("usage", "recent"), 0, 19)
        recent = [json.loads(item) for item in reversed(raw_recent)]

        return {
            "backend": self.name,
            "totals": totals,
            "by_model": by_model,
            "recent": recent,
        }

    async def close(self) -> None:
        await self.redis.aclose()


def stable_principal(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def build_state_backend(settings: Settings) -> StateBackend:
    mode = settings.state_backend.lower()
    if mode not in {"auto", "memory", "redis"}:
        raise ValueError("STATE_BACKEND must be auto, memory, or redis")

    if mode == "memory":
        return InMemoryStateBackend()

    if mode == "redis" and not settings.redis_url:
        raise ValueError("REDIS_URL is required when STATE_BACKEND=redis")

    if settings.redis_url:
        return RedisStateBackend(settings.redis_url, settings.redis_prefix)

    return InMemoryStateBackend()
