import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.budget import BudgetManager
from app.config import get_settings
from app.errors import GatewayError
from app.models import ChatCompletionRequest
from app.pricing import PricingCatalog
from app.rate_limit import RateLimiter
from app.resilience import CircuitBreaker
from app.router import ModelRouter
from app.security import require_api_key
from app.usage import UsageStore

settings = get_settings()
pricing = PricingCatalog(settings)
usage_store = UsageStore()
budget_manager = BudgetManager(settings, usage_store)
rate_limiter = RateLimiter(settings.rate_limit_requests_per_minute)
circuit_breaker = CircuitBreaker(
    failure_threshold=settings.circuit_failure_threshold,
    recovery_seconds=settings.circuit_recovery_seconds,
)
router = ModelRouter(settings, pricing=pricing, circuit_breaker=circuit_breaker)

app = FastAPI(
    title="Multi-LLM AI Gateway",
    version="0.2.0",
    description="OpenAI-compatible multi-provider LLM gateway with policy and cost governance.",
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(GatewayError)
async def gateway_error_handler(_request: Request, exc: GatewayError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/v1/providers", dependencies=[Depends(require_api_key)])
async def providers() -> dict[str, object]:
    return {"providers": router.provider_status()}


@app.get("/v1/models", dependencies=[Depends(require_api_key)])
async def models() -> dict[str, object]:
    return router.model_catalog()


@app.get("/v1/usage", dependencies=[Depends(require_api_key)])
async def usage() -> dict[str, object]:
    return usage_store.snapshot()


@app.get("/v1/budgets", dependencies=[Depends(require_api_key)])
async def budgets() -> dict[str, object]:
    return budget_manager.status()


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    response: Response,
    api_key: Annotated[str, Depends(require_api_key)],
):
    if payload.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported in v0.2")

    rate = rate_limiter.check(api_key)
    response.headers["X-RateLimit-Limit"] = str(rate.limit)
    response.headers["X-RateLimit-Remaining"] = str(rate.remaining)
    if not rate.allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(rate.retry_after_seconds)},
        )

    if not budget_manager.allowed():
        raise HTTPException(
            status_code=429,
            detail={"message": "Configured gateway budget is exhausted", **budget_manager.status()},
        )

    try:
        result, route_metadata = await router.route(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    raw_usage = result.get("usage", {})
    prompt_tokens = int(raw_usage.get("prompt_tokens", 0))
    completion_tokens = int(raw_usage.get("completion_tokens", 0))
    canonical_model = f"{route_metadata['provider']}:{route_metadata['model']}"
    cost_usd, pricing_known = pricing.calculate(
        canonical_model,
        prompt_tokens,
        completion_tokens,
    )

    usage_store.record(
        request_id=request.state.request_id,
        provider=str(route_metadata["provider"]),
        model=str(route_metadata["model"]),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        pricing_known=pricing_known,
    )

    route_metadata["cost_usd"] = round(cost_usd, 8)
    route_metadata["pricing_known"] = pricing_known
    route_metadata["budget"] = budget_manager.status()
    result["gateway"] = route_metadata
    return result
