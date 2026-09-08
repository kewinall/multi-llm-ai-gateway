import json
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.admin import router as admin_router
from app.admin_ui import admin_console
from app.budget import BudgetManager
from app.config import get_settings
from app.errors import GatewayError
from app.governance import GovernanceStore
from app.identity import OIDCAuthenticator
from app.models import ChatCompletionRequest
from app.observability import (
    configure_tracing,
    metrics_response,
    record_rejection,
    record_success,
    timer_start,
    tracer,
)
from app.policy import PolicyEngine
from app.rate_limit import RateLimiter
from app.resilience import CircuitBreaker
from app.router import ModelRouter
from app.security import Principal, require_api_key, require_operator
from app.state import build_state_backend
from app.usage import UsageStore

settings = get_settings()
state_backend = build_state_backend(settings)
governance = GovernanceStore(settings, state_backend)
identity = OIDCAuthenticator(settings)
policy_engine = PolicyEngine()
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
    governance=governance,
    circuit_breaker=circuit_breaker,
)
gateway_tracer = tracer(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await state_backend.close()


app = FastAPI(
    title="Multi-LLM AI Gateway",
    version="0.5.0",
    description=(
        "OpenAI-compatible enterprise AI gateway with streaming, OIDC identity, "
        "policy enforcement, dynamic governance, and distributed observability."
    ),
    lifespan=lifespan,
)
app.state.settings = settings
app.state.governance = governance
app.state.identity = identity
app.state.policy_engine = policy_engine
app.state.usage_store = usage_store
app.state.budget_manager = budget_manager
configure_tracing(app, settings)
app.include_router(admin_router)


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


@app.get("/admin", include_in_schema=False)
async def admin_ui():
    return admin_console()


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
    return await router.model_catalog()


@app.get("/v1/usage", dependencies=[Depends(require_api_key)])
async def usage() -> dict[str, object]:
    return await usage_store.snapshot()


@app.get("/v1/budgets", dependencies=[Depends(require_api_key)])
async def budgets() -> dict[str, object]:
    return await budget_manager.status()


def _calculate_cost(
    pricing: dict[str, dict[str, float]],
    canonical_model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> tuple[float, bool]:
    price = pricing.get(canonical_model)
    if price is None:
        return 0.0, False
    cost = (
        prompt_tokens * float(price.get("input_per_million", 0.0))
        + completion_tokens * float(price.get("output_per_million", 0.0))
    ) / 1_000_000
    return cost, True


async def _enforce_request_controls(
    payload: ChatCompletionRequest,
    principal: Principal,
) -> tuple[object, dict[str, object]]:
    snapshot = await governance.snapshot()
    decision = policy_engine.evaluate(
        snapshot["policies"],
        principal_id=principal.id,
        role=principal.role,
        request=payload,
    )
    if not decision.allowed:
        record_rejection("policy")
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Request denied by gateway policy",
                "policy": decision.policy,
                "reason": decision.reason,
            },
        )

    rate = await rate_limiter.check(
        principal.id,
        principal.rate_limit_requests_per_minute,
    )
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
    return rate, {
        "policy": decision.policy,
        "policy_reason": decision.reason,
    }


async def _stream_response(
    payload: ChatCompletionRequest,
    request: Request,
    principal: Principal,
    route_metadata: dict[str, object],
    source,
    started_at: float,
):
    prompt_tokens = 0
    completion_tokens = 0
    cost_usd = 0.0
    pricing_known = False

    async for chunk in source:
        raw_usage = chunk.get("usage", {})
        if raw_usage:
            prompt_tokens = int(raw_usage.get("prompt_tokens", 0))
            completion_tokens = int(raw_usage.get("completion_tokens", 0))
            snapshot = await governance.snapshot()
            canonical_model = (
                f"{route_metadata['provider']}:{route_metadata['model']}"
            )
            cost_usd, pricing_known = _calculate_cost(
                snapshot["pricing"],
                canonical_model,
                prompt_tokens,
                completion_tokens,
            )
            route_metadata["cost_usd"] = round(cost_usd, 8)
            route_metadata["pricing_known"] = pricing_known
            route_metadata["budget"] = await budget_manager.status()
            chunk["gateway"] = route_metadata

        yield f"data: {json.dumps(chunk, separators=(',', ':'))}\n\n"

    await usage_store.record(
        request_id=request.state.request_id,
        provider=str(route_metadata["provider"]),
        model=str(route_metadata["model"]),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        pricing_known=pricing_known,
    )
    record_success(
        metadata=route_metadata,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        started_at=started_at,
    )
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_operator)],
):
    started_at = timer_start()
    rate, policy_metadata = await _enforce_request_controls(payload, principal)
    headers = {
        "X-RateLimit-Limit": str(rate.limit),
        "X-RateLimit-Remaining": str(rate.remaining),
    }
    response.headers.update(headers)

    if payload.stream:
        try:
            source, route_metadata = await router.stream_route(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        route_metadata.update(policy_metadata)
        route_metadata["client"] = {
            "id": principal.id,
            "name": principal.name,
            "role": principal.role,
            "source": principal.source,
        }
        return StreamingResponse(
            _stream_response(
                payload,
                request,
                principal,
                route_metadata,
                source,
                started_at,
            ),
            media_type="text/event-stream",
            headers={
                **headers,
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    with gateway_tracer.start_as_current_span("llm.gateway.route") as span:
        span.set_attribute("llm.requested_model", payload.model)
        span.set_attribute("llm.client_id", principal.id)
        span.set_attribute("llm.client_role", principal.role)
        try:
            result, route_metadata = await router.route(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        raw_usage = result.get("usage", {})
        prompt_tokens = int(raw_usage.get("prompt_tokens", 0))
        completion_tokens = int(raw_usage.get("completion_tokens", 0))
        canonical_model = f"{route_metadata['provider']}:{route_metadata['model']}"
        governance_snapshot = await governance.snapshot()
        cost_usd, pricing_known = _calculate_cost(
            governance_snapshot["pricing"],
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

        route_metadata.update(policy_metadata)
        route_metadata["cost_usd"] = round(cost_usd, 8)
        route_metadata["pricing_known"] = pricing_known
        route_metadata["budget"] = await budget_manager.status()
        route_metadata["client"] = {
            "id": principal.id,
            "name": principal.name,
            "role": principal.role,
            "source": principal.source,
        }
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
