# 設定說明 / Configuration

本專案以環境變數設定 Gateway、Provider、路由、治理、Redis 與 OpenTelemetry。
正式環境請使用 Secret Manager、Kubernetes Secret、Vault 或雲端 Key Vault 保存敏感資訊。

## Gateway

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_API_KEY` | `dev-gateway-key` | Client key required in `X-API-Key` |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Upstream HTTP timeout |
| `MODEL_ALIASES_JSON` | `{"default":"mock:demo"}` | Stable alias -> `provider:model` |
| `MODEL_POOLS_JSON` | `{}` | Logical pool -> candidate model array |
| `FALLBACK_MODELS_JSON` | `[]` | Global fallback candidates |
| `ROUTING_POLICY` | `priority` | Default routing policy |
| `MODEL_PRICING_JSON` | mock price = 0 | USD pricing per 1M tokens |

## Governance

| Variable | Default | Description |
|---|---:|---|
| `PROVIDER_RETRY_ATTEMPTS` | 1 | Retry count per candidate |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | 60 | Sliding-window limit per API key |
| `DAILY_BUDGET_USD` | disabled | Daily hard limit |
| `MONTHLY_BUDGET_USD` | disabled | Monthly hard limit |
| `CIRCUIT_FAILURE_THRESHOLD` | 3 | Failures before circuit opens |
| `CIRCUIT_RECOVERY_SECONDS` | 30 | Recovery window |

## Distributed state

| Variable | Default | Description |
|---|---|---|
| `STATE_BACKEND` | `auto` | `auto`, `memory`, or `redis` |
| `REDIS_URL` | empty | Redis connection URL |
| `REDIS_PREFIX` | `llm-gateway` | Namespace for Gateway keys |

Behavior:

- `auto`: use Redis when `REDIS_URL` exists, otherwise memory
- `memory`: always process-local memory
- `redis`: Redis is mandatory; `REDIS_URL` must be set

Example:

```dotenv
STATE_BACKEND=redis
REDIS_URL=redis://redis:6379/0
REDIS_PREFIX=llm-gateway
```

## OpenTelemetry

| Variable | Default | Description |
|---|---|---|
| `OTEL_SERVICE_NAME` | `multi-llm-ai-gateway` | OTel resource service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty | OTLP/HTTP trace endpoint |

When the OTLP endpoint is empty, tracing exporters/instrumentation are not installed at runtime.
Prometheus metrics remain available.

## Providers

| Provider | Credential | Base URL variable |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` |
| Google Gemini | `GOOGLE_API_KEY` | `GOOGLE_BASE_URL` |
| Mock | none | none |

## Routing policies

- `priority`: preserve configured candidate order
- `round_robin`: rotate candidate order; cursor is shared in Redis
- `random`: shuffle candidates per request
- `cost`: sort by configured input + output price

Request override:

```json
{
  "model": "balanced",
  "routing_policy": "cost",
  "messages": [{"role": "user", "content": "Hello"}]
}
```

## Budget behavior

Budget checks use accumulated actual cost. When a daily or monthly limit is already exhausted,
new Chat Completion requests return HTTP 429. v0.3 still does not predict the cost of the pending
request before it is executed.

## Readiness

`GET /ready` checks the active state backend. Redis failure produces HTTP 503, making the endpoint
appropriate for Kubernetes readiness probes and load-balancer health routing.

## Security note

The built-in API key remains a reference implementation. Enterprise deployment should integrate
TLS, OIDC/JWT, workload identity, secret rotation, audit logging, WAF/network policy, Redis
authentication/TLS, and organization-standard observability access controls.
