# Multi-LLM AI Gateway

> 企業級多模型 AI Gateway 範例 / Enterprise multi-provider AI gateway reference implementation.

An **OpenAI-compatible Enterprise AI Gateway** that decouples applications from LLM vendors and
centralizes routing, resilience, cost governance, distributed state, observability, RBAC, and
runtime model governance.

## v0.4 Features

- **Unified API**: `POST /v1/chat/completions`
- **Providers**: OpenAI, Anthropic, Google Gemini, Mock
- **Routing**: priority, round-robin, random, cost-aware
- **Fallback, retry, circuit breaker**
- **Token / cost accounting and daily/monthly budgets**
- **Per-client rate limiting**
- **Redis distributed state and governance**
- **Dynamic aliases, model pools, pricing, and routing policy without restart**
- **Managed API clients with hashed keys**
- **RBAC**: viewer / operator / admin
- **Audit log** for governance changes
- **Embedded Admin Console** at `/admin`
- **Prometheus + OpenTelemetry + Grafana**
- **Helm chart** with multi-replica production defaults
- **CI validation**: Ruff, Pytest, Redis integration, Docker, Compose, Helm
- **Gated automatic GitHub Releases**

## Architecture

```text
                  +---------------------------+
                  | Client / Agent / RAG      |
                  +-------------+-------------+
                                |
                       API Key + RBAC
                                |
                                v
                  +---------------------------+
                  | Multi-LLM AI Gateway      |
                  |                           |
                  | Rate Limit -> Budget      |
                  |        |                  |
                  | Dynamic Governance        |
                  |        |                  |
                  | Model / Policy Router     |
                  +----+------+-------+-------+
                       |      |       |
                    OpenAI Anthropic Gemini
                                |
                     Usage / Cost / Trace
                                |
             +------------------+------------------+
             |                  |                  |
          Redis             Prometheus          OTEL
   state + governance         /metrics          traces
             |                  |
       multi replicas          Grafana

Admin Console /admin
      |
      +-- aliases / pools / pricing / policy
      +-- API clients / RBAC
      +-- audit log
```

## Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Default local credentials:

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

## Docker Compose stack

```bash
cp .env.example .env
docker compose up --build
```

Includes Gateway, Redis, Prometheus, Grafana, and OpenTelemetry Collector.

## RBAC

| Role | Read APIs | Chat Completion | Admin APIs |
|---|---:|---:|---:|
| viewer | Yes | No | No |
| operator | Yes | Yes | No |
| admin | Yes | Yes | Yes |

The legacy `GATEWAY_API_KEY` remains a bootstrap `operator`.
`ADMIN_API_KEY` is a bootstrap `admin`.

Managed client keys are returned only at creation time. Only a SHA-256 digest is stored in the
governance backend.

## Dynamic governance

The Admin API can update aliases, pools, pricing, and the default routing policy at runtime.
With Redis active, the changes are visible to every Gateway replica immediately.

Example:

```bash
curl -X PUT http://localhost:8000/admin/api/aliases/quality \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{"target":"mock:quality"}'
```

No application restart is required.

## Enterprise Kubernetes deployment

A Helm chart is included at:

```text
deploy/helm/multi-llm-ai-gateway
```

Validate and render it:

```bash
helm lint deploy/helm/multi-llm-ai-gateway
helm template ai-gateway deploy/helm/multi-llm-ai-gateway
```

The chart provides 2 replicas by default, health/readiness probes, PodDisruptionBudget, hardened
pod/container security contexts, resource limits, Prometheus annotations, optional HPA, and
optional Ingress.

## API surface

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible model invocation |
| `GET /v1/providers` | Provider + circuit status |
| `GET /v1/models` | Effective aliases, pools, pricing, policy |
| `GET /v1/usage` | Request/token/cost accounting |
| `GET /v1/budgets` | Budget status |
| `GET /admin` | Admin Console |
| `/admin/api/*` | Runtime governance and client management |
| `GET /health` | Liveness |
| `GET /ready` | Backend readiness |
| `GET /metrics` | Prometheus metrics |

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Admin Console](docs/admin-console.md)
- [Enterprise Deployment](docs/enterprise-deployment.md)
- [Distributed State](docs/distributed-state.md)
- [Observability](docs/observability.md)
- [Usage Examples](docs/usage.md)

## Release flow

```text
Version change
   |
   +-- Quality:
   |     Ruff
   |     Pytest
   |     Redis integration
   |     Docker build
   |     Docker Compose config
   |     Helm lint + template
   |
   +-- Security:
   |     Secret check
   |     pip-audit
   |
   +-- Git tag + GitHub Release
```

## Roadmap

- **v0.1** — unified chat API, adapters, routing, fallback
- **v0.2** — routing policies, retries, budgets, cost accounting, rate limits
- **v0.3** — Redis distributed state, Prometheus, OpenTelemetry, Grafana
- **v0.4** — Admin Console, dynamic governance, client RBAC, audit, Helm deployment
- **v0.5** — streaming, richer enterprise identity/policy integration, deployment hardening

## 專案定位 / Project positioning

此專案展示企業 AI Platform 如何把 RAG、Agent、內部應用與 LLM Provider 解耦，集中處理
**Model Routing、Resilience、Cost Governance、Distributed State、Observability、RBAC、
Runtime Governance 與 Kubernetes Deployment**。

## License

MIT
