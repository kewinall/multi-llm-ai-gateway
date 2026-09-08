# 可觀測性 / Observability

v0.3 adds Prometheus metrics, OpenTelemetry tracing, readiness checks, and a provisioned Grafana dashboard.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Process health and active state backend |
| `GET /ready` | Backend readiness; returns 503 when Redis is unavailable |
| `GET /metrics` | Prometheus exposition format |

## Prometheus metrics

The gateway exports:

- `llm_gateway_requests_total`
- `llm_gateway_tokens_total`
- `llm_gateway_cost_usd_total`
- `llm_gateway_provider_attempts_total`
- `llm_gateway_request_duration_seconds`
- `llm_gateway_rate_limited_total`
- `llm_gateway_budget_rejected_total`

Useful queries:

```promql
sum(rate(llm_gateway_requests_total[5m]))
```

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(llm_gateway_request_duration_seconds_bucket[5m]))
)
```

```promql
sum by (provider, model) (increase(llm_gateway_cost_usd_total[1h]))
```

## OpenTelemetry

Set:

```dotenv
OTEL_SERVICE_NAME=multi-llm-ai-gateway
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
```

When the endpoint is configured, FastAPI inbound requests and HTTPX outbound provider requests are instrumented. The router also emits explicit `llm.gateway.route` and `llm.provider.request` spans with provider/model/routing attributes.

The included Docker Compose stack sends OTLP/HTTP traces to the OpenTelemetry Collector, whose default demo exporter prints trace summaries to collector logs.

## Grafana

The Compose stack provisions:

- Prometheus datasource
- AI Gateway dashboard
- request rate
- p95 latency
- token throughput
- cost rate
- provider attempts
- request/model breakdown

Open:

```text
http://localhost:3000
```

Default demo account:

```text
admin / admin
```

Set `GRAFANA_ADMIN_PASSWORD` before shared or non-local use.

## Production note

The provided observability stack is a reference deployment. Production environments should use the organization's managed Prometheus/Grafana/OTLP backend, retention policy, authentication, TLS, and access-control standards.
