import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.requests_per_minute = requests_per_minute
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()

    def check(self, key: str, now: float | None = None) -> RateLimitResult:
        current = time.monotonic() if now is None else now
        window_start = current - 60.0

        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= self.requests_per_minute:
                retry_after = max(1, int(60 - (current - bucket[0])))
                return RateLimitResult(
                    allowed=False,
                    limit=self.requests_per_minute,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            bucket.append(current)
            remaining = max(self.requests_per_minute - len(bucket), 0)

        return RateLimitResult(
            allowed=True,
            limit=self.requests_per_minute,
            remaining=remaining,
            retry_after_seconds=0,
        )
