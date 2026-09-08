from time import perf_counter
from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from app.config import Settings

REQUESTS = Counter(
    "llm_gateway_requests_total",
    "Gateway chat completion requests.",
    ["status", "provider", "model", "policy"],
)
TOKENS = Counter(
    "llm_gateway_tokens_total",
    "LLM tokens processed by the gateway.",
    ["type", "provider", "model"],
)
COST = Counter(
    "llm_gateway_cost_usd_total",
    "Estimated LLM cost in USD.",
    ["provider", "model"],
)
ATTEMPTS = Counter(
    "llm_gateway_provider_attempts_total",
    "Provider attempts performed by the router.",
    ["provider", "status"],
)
LATENCY = Histogram(
    "llm_gateway_request_duration_seconds",
    "Chat completion request latency.",
    ["provider", "model", "policy"],
)
RATE_LIMITED = Counter(
    "llm_gateway_rate_limited_total",
    "Requests rejected by rate limiting.",
)
BUDGET_REJECTED = Counter(
    "llm_gateway_budget_rejected_total",
    "Requests rejected by configured budgets.",
)


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def configure_tracing(app: FastAPI, settings: Settings) -> bool:
    if not settings.otel_exporter_otlp_endpoint:
        return False

    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name})
    )
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    return True


def tracer(name: str):
    return trace.get_tracer(name)


def timer_start() -> float:
    return perf_counter()


def record_success(
    *,
    metadata: dict[str, Any],
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    started_at: float,
) -> None:
    provider = str(metadata["provider"])
    model = str(metadata["model"])
    policy = str(metadata["routing_policy"])

    REQUESTS.labels("success", provider, model, policy).inc()
    TOKENS.labels("prompt", provider, model).inc(prompt_tokens)
    TOKENS.labels("completion", provider, model).inc(completion_tokens)
    COST.labels(provider, model).inc(cost_usd)
    LATENCY.labels(provider, model, policy).observe(perf_counter() - started_at)

    for attempt in metadata.get("attempts", []):
        target = str(attempt["target"])
        attempt_provider = target.split(":", 1)[0]
        ATTEMPTS.labels(attempt_provider, str(attempt["status"])).inc()


def record_rejection(kind: str) -> None:
    if kind == "rate_limit":
        RATE_LIMITED.inc()
    elif kind == "budget":
        BUDGET_REJECTED.inc()
