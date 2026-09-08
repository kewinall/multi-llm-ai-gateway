# 設定說明 / Configuration

v0.5 combines bootstrap environment configuration with Redis/memory runtime governance.

## Bootstrap credentials

| Variable | Default | Purpose |
|---|---|---|
| `GATEWAY_API_KEY` | `dev-gateway-key` | Bootstrap operator |
| `ADMIN_API_KEY` | `dev-admin-key` | Bootstrap administrator |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Upstream request timeout |

## OIDC / JWT

OIDC is disabled unless issuer, audience and JWKS URL are all configured.

| Variable | Default |
|---|---|
| `OIDC_ISSUER` | empty |
| `OIDC_AUDIENCE` | empty |
| `OIDC_JWKS_URL` | empty |
| `OIDC_ROLE_CLAIM` | `roles` |
| `OIDC_NAME_CLAIM` | `preferred_username` |
| `OIDC_DEFAULT_ROLE` | `viewer` |
| `OIDC_ALGORITHMS_CSV` | `RS256` |
| `OIDC_JWKS_CACHE_SECONDS` | `300` |

Example:

```dotenv
OIDC_ISSUER=https://login.example.com/
OIDC_AUDIENCE=enterprise-ai-gateway
OIDC_JWKS_URL=https://login.example.com/.well-known/jwks.json
OIDC_ROLE_CLAIM=roles
OIDC_NAME_CLAIM=preferred_username
OIDC_DEFAULT_ROLE=viewer
OIDC_ALGORITHMS_CSV=RS256
```

## Static governance defaults

| Variable | Default |
|---|---|
| `MODEL_ALIASES_JSON` | `{"default":"mock:demo"}` |
| `MODEL_POOLS_JSON` | `{}` |
| `FALLBACK_MODELS_JSON` | `[]` |
| `MODEL_PRICING_JSON` | mock = zero cost |
| `POLICIES_JSON` | `{}` |
| `ROUTING_POLICY` | `priority` |

Runtime Admin API overrides take precedence.

## Request policy

Policy structure:

```json
{
  "enabled": true,
  "priority": 10,
  "effect": "allow",
  "roles": ["operator"],
  "clients": ["oidc:user-1"],
  "models": ["openai:*"],
  "allow_stream": true,
  "max_tokens": 4096
}
```

All match fields are optional. Model matching uses glob semantics.

## Governance / resilience

| Variable | Default |
|---|---:|
| `PROVIDER_RETRY_ATTEMPTS` | 1 |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | 60 |
| `DAILY_BUDGET_USD` | disabled |
| `MONTHLY_BUDGET_USD` | disabled |
| `CIRCUIT_FAILURE_THRESHOLD` | 3 |
| `CIRCUIT_RECOVERY_SECONDS` | 30 |

## Distributed backend

| Variable | Default |
|---|---|
| `STATE_BACKEND` | `auto` |
| `REDIS_URL` | empty |
| `REDIS_PREFIX` | `llm-gateway` |

Production should configure Redis authentication/TLS and HA.

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

## Streaming

No extra environment flag is required. Clients set:

```json
{"stream": true}
```

Policy can independently allow/deny stream usage.

## Kubernetes

Helm exposes OIDC configuration via ConfigMap while API/provider/Redis secrets remain sourced from
the configured Kubernetes Secret.

See [Enterprise Deployment](enterprise-deployment.md).

## Security notes

- replace bootstrap dev keys in every non-local environment
- prefer managed client keys or enterprise OIDC identity
- use HTTPS/TLS at ingress
- use TLS/authenticated Redis
- scope NetworkPolicy to your actual ingress and egress dependencies
- use external secret management
- rotate managed API client keys periodically
