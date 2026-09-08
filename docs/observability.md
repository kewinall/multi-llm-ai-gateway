# 可觀測性 / Observability

v0.5 exposes Prometheus metrics, OpenTelemetry traces, readiness, and a provisioned Grafana
dashboard for buffered and streaming traffic.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Process health and active state backend |
| `GET /ready` | Backend readiness; 503 when Redis is unavailable |
| `GET /metrics` | Prometheus exposition format |

## Prometheus metrics

The Gateway exports:

- `llm_gateway_requests_total`
- `llm_gateway_tokens_total`
- `llm_gateway_cost_usd_total`
- `llm_gateway_provider_attempts_total`
- `llm_gateway_request_duration_seconds`
- `llm_gateway_rate_limited_total`
- `llm_gateway_budget_rejected_total`
- `llm_gateway_policy_rejected_total`

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

```promql
sum(increase(llm_gateway_policy_rejected_total[1h]))
```

## Streaming accounting

For a completed SSE request, request/token/cost metrics are finalized when the stream completes and
usage metadata is available. Mock and OpenAI streaming paths are covered by automated tests.

## OpenTelemetry

Set:

```dotenv
OTEL_SERVICE_NAME=multi-llm-ai-gateway
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
```

FastAPI inbound and HTTPX outbound calls are instrumented when OTLP export is enabled. Explicit
route/provider spans continue to capture provider/model/routing information.

## Grafana

The included dashboard contains:

- request rate
- p95 latency
- estimated cost rate
- rate-limit rejects
- policy rejects
- token throughput
- provider attempts
- requests by model
- cost by model

Open:

```text
http://localhost:3000
```

The Compose deployment is a reference stack. Production should use organization-approved
authentication, TLS, retention, dashboards, alerting, and observability access controls.
