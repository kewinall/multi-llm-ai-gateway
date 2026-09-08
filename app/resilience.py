import time
from dataclasses import dataclass
from threading import Lock


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_seconds: float) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._states: dict[str, CircuitState] = {}
        self._lock = Lock()

    def reset(self) -> None:
        with self._lock:
            self._states.clear()

    def allow(self, provider: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        with self._lock:
            state = self._states.get(provider)
            if state is None or state.opened_at is None:
                return True
            if current - state.opened_at >= self.recovery_seconds:
                return True
            return False

    def success(self, provider: str) -> None:
        with self._lock:
            self._states[provider] = CircuitState()

    def failure(self, provider: str, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        with self._lock:
            state = self._states.setdefault(provider, CircuitState())
            state.failures += 1
            if state.failures >= self.failure_threshold:
                state.opened_at = current

    def status(self, provider: str, now: float | None = None) -> dict[str, object]:
        current = time.monotonic() if now is None else now
        with self._lock:
            state = self._states.get(provider, CircuitState())
            opened_at = state.opened_at
            failures = state.failures

        if opened_at is None:
            name = "closed"
        elif current - opened_at >= self.recovery_seconds:
            name = "half_open"
        else:
            name = "open"

        return {"state": name, "failures": failures}
