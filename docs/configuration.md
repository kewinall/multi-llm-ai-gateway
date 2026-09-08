# 設定說明 / Configuration

v0.4 combines environment bootstrap configuration with runtime governance overrides.

## Bootstrap credentials

| Variable | Default | Purpose |
|---|---|---|
| `GATEWAY_API_KEY` | `dev-gateway-key` | Backward-compatible bootstrap operator |
| `ADMIN_API_KEY` | `dev-admin-key` | Bootstrap administrator / Admin Console |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Upstream timeout |

Local Admin API usage:

```text
X-Admin-Key: dev-admin-key
```

Managed admin clients may instead authenticate with `X-API-Key`.

## Static governance defaults

| Variable | Default |
|---|---|
| `MODEL_ALIASES_JSON` | `{"default":"mock:demo"}` |
| `MODEL_POOLS_JSON` | `{}` |
| `FALLBACK_MODELS_JSON` | `[]` |
| `MODEL_PRICING_JSON` | mock = zero cost |
| `ROUTING_POLICY` | `priority` |

These values are bootstrap defaults. Admin API runtime overrides take precedence.

## Runtime governance

Managed at `/admin/api/*`:

- aliases
- pools
- pricing
- routing policy
- managed API clients
- audit events

When Redis is active, these settings are distributed across replicas.

## Governance / resilience

| Variable | Default |
|---|---:|
| `PROVIDER_RETRY_ATTEMPTS` | 1 |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | 60 |
| `DAILY_BUDGET_USD` | disabled |
| `MONTHLY_BUDGET_USD` | disabled |
| `CIRCUIT_FAILURE_THRESHOLD` | 3 |
| `CIRCUIT_RECOVERY_SECONDS` | 30 |

A managed client may override the global RPM limit.

## Distributed backend

| Variable | Default | Description |
|---|---|---|
| `STATE_BACKEND` | `auto` | auto / memory / redis |
| `REDIS_URL` | empty | Redis connection URL |
| `REDIS_PREFIX` | `llm-gateway` | Key namespace |

Production:

```dotenv
STATE_BACKEND=redis
REDIS_URL=redis://redis.example.internal:6379/0
REDIS_PREFIX=llm-gateway
```

Use Redis authentication/TLS in production.

## Providers

| Provider | Credential | Endpoint |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` |
| Google Gemini | `GOOGLE_API_KEY` | `GOOGLE_BASE_URL` |
| Mock | none | built in |

## OpenTelemetry

| Variable | Default |
|---|---|
| `OTEL_SERVICE_NAME` | `multi-llm-ai-gateway` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty |

Prometheus metrics remain available even when OTLP export is disabled.

## Enterprise deployment

The Helm chart reads runtime configuration from a ConfigMap and credentials from an existing
Kubernetes Secret. See [Enterprise Deployment](enterprise-deployment.md).

## Security note

Default development credentials must not be retained outside local/demo environments. Production
should use organization-approved secret management, TLS, Redis TLS/authentication, API ingress
controls, and ideally external enterprise identity such as OIDC/workload identity in a future
integration layer.
