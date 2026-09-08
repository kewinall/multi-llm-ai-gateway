from app.state import RateLimitState, StateBackend, stable_principal


class RateLimiter:
    def __init__(self, backend: StateBackend, requests_per_minute: int) -> None:
        self.backend = backend
        self.requests_per_minute = requests_per_minute

    async def reset(self) -> None:
        await self.backend.reset()

    async def check(self, principal: str) -> RateLimitState:
        return await self.backend.rate_limit(
            stable_principal(principal),
            limit=self.requests_per_minute,
            window_seconds=60,
        )
