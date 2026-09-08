from app.state import StateBackend


class CircuitBreaker:
    def __init__(
        self,
        backend: StateBackend,
        failure_threshold: int,
        recovery_seconds: float,
    ) -> None:
        self.backend = backend
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds

    async def reset(self) -> None:
        await self.backend.reset()

    async def allow(self, provider: str) -> bool:
        return await self.backend.circuit_allow(provider, self.recovery_seconds)

    async def success(self, provider: str) -> None:
        await self.backend.circuit_success(provider)

    async def failure(self, provider: str) -> None:
        await self.backend.circuit_failure(provider, self.failure_threshold)

    async def status(self, provider: str) -> dict[str, object]:
        return await self.backend.circuit_status(provider, self.recovery_seconds)
