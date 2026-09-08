import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.budget import BudgetManager
from app.config import get_settings
from app.errors import GatewayError
from app.models import ChatCompletionRequest
from app.observability import (
    configure_tracing,
    metrics_response,
    record_rejection,
    record_success,
    timer_start,
    tracer,
)
from app.pricing import PricingCatalog
from app.rate_limit import RateLimiter
from app.resilience import CircuitBreaker
from app.router import ModelRouter
from app.security import require_api_key
from app.state import build_state_backend
from app.usage import UsageStore

settings = get_settings()
state_backend = build_state_backend(settings)
pricing = PricingCatalog(settings)
usage_store = UsageStore(state_backend)
budget_manager = BudgetManager(settings, usage_store)
rate_limiter = RateLimiter(state_backend, settings.rate_limit_requests_per_minute)
circuit_breaker = CircuitBreaker(
    state_backend,
    failure_threshold=settings.circuit_failure_threshold,
    recovery_seconds=settings.circuit_recovery_seconds,
)
router = ModelRouter(
    settings,
    state_backend=state_backend,
    pricing=pricing,
    circuit_breaker=circuit_breaker,
)
gateway_tracer = tracer(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await state_backend.close()


app = FastAPI(
    title="Multi-LLM AI Gateway",
    version="0.3.0",
    description=(
        "OpenAI-compatible multi-provider LLM gateway with distributed governance "
        "and observability."
    ),
    lifespan=lifespan,
)
configure_tracing(app, settings)


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
    return {
        "status": "ok",
        "version": app.version,
        "state_backend": state_backend.name,
    }


@app.get("/ready")
async def ready() -> JSONResponse:
    healthy = await state_backend.health()
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "ready": healthy,
            "state_backend": state_backend.name,
        },
    )


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return metrics_response()


@app.get("/v1/providers", dependencies=[Depends(require_api_key)])
async def providers() -> dict[str, object]:
    return {"providers": await router.provider_status()}


@app.get("/v1/models", dependencies=[Depends(require_api_key)])
async def models() -> dict[str, object]:
    return router.model_catalog()


@app.get("/v1/usage", dependencies=[Depends(require_api_key)])
async def usage() -> dict[str, object]:
    return await usage_store.snapshot()


@app.get("/v1/budgets", dependencies=[Depends(require_api_key)])
async def budgets() -> dict[str, object]:
    return await budget_manager.status()


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    response: Response,
    api_key: Annotated[str, Depends(require_api_key)],
):
    started_at = timer_start()
    if payload.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported in v0.3")

    rate = await rate_limiter.check(api_key)
    response.headers["X-RateLimit-Limit"] = str(rate.limit)
    response.headers["X-RateLimit-Remaining"] = str(rate.remaining)
    if not rate.allowed:
        record_rejection("rate_limit")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(rate.retry_after_seconds)},
        )

    if not await budget_manager.allowed():
        record_rejection("budget")
        budget_status = await budget_manager.status()
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Configured gateway budget is exhausted",
                **budget_status,
            },
        )

    with gateway_tracer.start_as_current_span("llm.gateway.route") as span:
        span.set_attribute("llm.requested_model", payload.model)
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

        await usage_store.record(
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
        route_metadata["budget"] = await budget_manager.status()
        result["gateway"] = route_metadata

        span.set_attribute("llm.selected_provider", str(route_metadata["provider"]))
        span.set_attribute("llm.selected_model", str(route_metadata["model"]))
        span.set_attribute("llm.cost_usd", cost_usd)

    record_success(
        metadata=route_metadata,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        started_at=started_at,
    )
    return result
