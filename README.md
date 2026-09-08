# Multi-LLM AI Gateway

> 企業級多模型 AI Gateway 範例 / Enterprise multi-provider AI gateway reference implementation.

An **OpenAI-compatible Enterprise AI Gateway** that decouples applications from LLM vendors and
centralizes routing, resilience, cost governance, streaming, enterprise identity, runtime policy,
distributed state, observability, and Kubernetes deployment.

## v0.5 Features

- **Unified API**: `POST /v1/chat/completions`
- **OpenAI-compatible SSE streaming**
- **Native progressive streaming** for Mock and OpenAI
- **Normalized stream contract** for Anthropic and Google Gemini
- **Providers**: OpenAI, Anthropic, Google Gemini, Mock
- **Routing**: priority, round-robin, random, cost-aware
- **Fallback, retry, circuit breaker**
- **Token / cost accounting and daily/monthly budgets**
- **Redis distributed state and runtime governance**
- **Dynamic aliases, pools, pricing, routing policy**
- **Managed API clients with one-time plaintext keys**
- **API key rotation**
- **RBAC**: viewer / operator / admin
- **Optional OIDC/JWT bearer authentication**
- **JWKS signature, issuer, audience, expiry validation**
- **Runtime Policy Engine**
- **Policy match by role, client, model glob, streaming, max_tokens**
- **Governance audit log**
- **Embedded Admin Console**
- **Prometheus + OpenTelemetry + Grafana**
- **Policy rejection metric**
- **Helm chart with hardened pod defaults**
- **Optional NetworkPolicy**
- **Optional Prometheus ServiceMonitor**
- **CI validation**: Ruff, Pytest, Redis integration, Docker, Compose, Helm
- **Gated semantic GitHub Release workflow**

## Architecture

```text
                    Enterprise Identity
                 API Key         OIDC JWT
                    \             /
                     +-----------+
                          |
                       Principal
                 viewer/operator/admin
                          |
                          v
Client / RAG / Agent -> Policy Engine
                          |
                     Rate / Budget
                          |
                  Dynamic Governance
                          |
                  Model Policy Router
                   /      |       \
               OpenAI  Anthropic  Gemini
                   \      |       /
                    Stream / Response
                          |
                Usage / Cost / Audit
                          |
             +------------+------------+
             |            |            |
           Redis      Prometheus      OTEL
             |            |            |
       multi replicas   Grafana     Collector

Admin Console
  |- aliases / pools / pricing
  |- routing policy
  |- request policies
  |- API clients / RBAC
  |- key rotation
  '- audit
```

## Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Default local bootstrap credentials:

```text
X-API-Key:   dev-gateway-key
X-Admin-Key: dev-admin-key
```

Open:

| Surface | URL |
|---|---|
| Swagger UI | http://localhost:8000/docs |
| Admin Console | http://localhost:8000/admin |
| Health | http://localhost:8000/health |
| Readiness | http://localhost:8000/ready |
| Metrics | http://localhost:8000/metrics |

## Streaming

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-gateway-key' \
  -d '{
    "model":"mock:demo",
    "stream":true,
    "messages":[{"role":"user","content":"Hello stream"}]
  }'
```

The response uses `text/event-stream` and terminates with:

```text
data: [DONE]
```

## OIDC / JWT

OIDC is optional and does not break API-key authentication.

```dotenv
OIDC_ISSUER=https://id.example.com/
OIDC_AUDIENCE=ai-gateway
OIDC_JWKS_URL=https://id.example.com/.well-known/jwks.json
OIDC_ROLE_CLAIM=roles
OIDC_DEFAULT_ROLE=viewer
```

Then clients may use:

```http
Authorization: Bearer <signed-jwt>
```

The Gateway validates the JWT signature against JWKS plus issuer, audience, `exp`, `iat`, and
`sub`.

## Policy Engine

Example: deny streaming for operator requests to mock models.

```bash
curl -X PUT http://localhost:8000/admin/api/policies/no-stream \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "priority":10,
    "effect":"allow",
    "roles":["operator"],
    "models":["mock:*"],
    "allow_stream":false
  }'
```

Policy fields:

```text
enabled
priority
effect
roles
clients
models
allow_stream
max_tokens
```

Rules are evaluated by ascending priority with first-match behavior.

## API key rotation

```http
POST /admin/api/clients/{client_id}/rotate-key
```

The new plaintext key is returned once and the previous key is immediately invalidated.

## Docker Compose stack

```bash
cp .env.example .env
docker compose up --build
```

Includes Gateway, Redis, Prometheus, Grafana, and OpenTelemetry Collector.

## Enterprise Kubernetes deployment

Helm chart:

```text
deploy/helm/multi-llm-ai-gateway
```

Validation:

```bash
helm lint deploy/helm/multi-llm-ai-gateway
helm template ai-gateway deploy/helm/multi-llm-ai-gateway

helm template ai-gateway-hardened deploy/helm/multi-llm-ai-gateway \
  --set networkPolicy.enabled=true \
  --set serviceMonitor.enabled=true
```

Chart capabilities include:

- two replicas by default
- liveness/readiness
- PodDisruptionBudget
- non-root fixed UID/GID
- RuntimeDefault seccomp
- no privilege escalation
- all Linux capabilities dropped
- read-only root filesystem
- service account token disabled
- resource requests/limits
- optional HPA
- optional Ingress
- optional NetworkPolicy
- optional Prometheus ServiceMonitor
- external Secret contract

## API surface

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | Buffered or SSE Chat Completion |
| `GET /v1/providers` | Provider and circuit status |
| `GET /v1/models` | Effective governance snapshot |
| `GET /v1/usage` | Request/token/cost accounting |
| `GET /v1/budgets` | Budget status |
| `GET /admin` | Admin Console |
| `PUT /admin/api/policies/{name}` | Create/update request policy |
| `DELETE /admin/api/policies/{name}` | Delete request policy |
| `POST /admin/api/clients/{id}/rotate-key` | Rotate managed client key |
| `GET /admin/api/audit` | Governance audit |
| `GET /health` | Liveness |
| `GET /ready` | Backend readiness |
| `GET /metrics` | Prometheus metrics |

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Streaming](docs/streaming.md)
- [Enterprise Identity & Policy](docs/identity-policy.md)
- [Admin Console](docs/admin-console.md)
- [Enterprise Deployment](docs/enterprise-deployment.md)
- [Distributed State](docs/distributed-state.md)
- [Observability](docs/observability.md)
- [Usage Examples](docs/usage.md)

## Release flow

```text
Version change
   |
   +-- Quality
   |    |- Ruff
   |    |- Pytest
   |    |- Redis integration
   |    |- Docker build
   |    |- Compose config
   |    |- Helm lint
   |    '- Helm normal + hardening template render
   |
   +-- Security
   |    |- tracked secret check
   |    '- pip-audit
   |
   '-- semantic Git tag + GitHub Release
```

## Roadmap

- **v0.1** — unified multi-provider API
- **v0.2** — routing, fallback, retry, budgets, cost, rate limits
- **v0.3** — Redis distributed state, Prometheus, OpenTelemetry, Grafana
- **v0.4** — Admin Console, runtime governance, client RBAC, Helm
- **v0.5** — streaming, OIDC/JWT, request policies, key rotation, Kubernetes hardening
- **v0.6** — deeper provider-native streaming, external policy/identity integration, HA operations

## 專案定位 / Project positioning

此專案展示企業 AI Platform 如何集中處理 **Model Routing、Streaming、Resilience、
Cost Governance、OIDC/JWT、RBAC、Policy Enforcement、Distributed Governance、
Observability 與 Kubernetes Production Deployment**。

## License

MIT
