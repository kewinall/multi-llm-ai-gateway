# 架構設計 / Architecture

## 目標 / Goal

v0.4 在 v0.3 分散式 Gateway 基礎上加入 **management plane**：Runtime Governance、
Managed API Clients、RBAC、Audit 與 Kubernetes/Helm deployment。

## Logical architecture

```text
                    Management Plane
                +------------------------+
                | Admin Console / API    |
                | alias / pool / price   |
                | policy / clients / RBAC|
                | audit                  |
                +-----------+------------+
                            |
                     Governance Store
                            |
                  +---------+---------+
                  |                   |
               Memory               Redis
                                    |
                              shared replicas

                    Data Plane
Client -> Authentication / RBAC
       -> Rate Limit
       -> Budget
       -> Effective Governance Snapshot
       -> Model / Policy Router
       -> Circuit Breaker / Retry / Fallback
       -> Provider Adapter
       -> Usage / Cost / Metrics / Trace
       -> OpenAI-compatible Response
```

## Authentication and RBAC

A request resolves to a `Principal`.

| Credential | Effective role |
|---|---|
| `ADMIN_API_KEY` | bootstrap admin |
| `GATEWAY_API_KEY` | bootstrap operator |
| Managed client key | configured viewer/operator/admin |

Managed API keys are generated once, returned once, then represented only by SHA-256 digest in the
governance store.

### Role behavior

- `viewer`: read model/provider/usage/budget APIs
- `operator`: viewer capabilities + Chat Completion
- `admin`: operator capabilities + management APIs

## Dynamic governance

The effective configuration is:

```text
Environment defaults
       +
Runtime governance overrides
       =
Effective snapshot
```

Runtime overrides include:

- alias -> provider:model
- model pool -> candidate list
- model pricing
- default routing policy

The router reads this snapshot per request. There is no process restart for a governance update.

With Redis backend, every replica sees the same governance state.

## Distributed state

Redis now holds both operational state and management-plane state:

```text
rate limits
round-robin cursor
circuit breaker
usage / cost
budget counters
recent usage
dynamic aliases
dynamic pools
dynamic pricing
dynamic routing settings
managed API clients
audit events
```

## Observability

- Prometheus: `/metrics`
- OpenTelemetry: inbound FastAPI, outbound HTTPX, route/provider spans
- Grafana: provisioned AI Gateway dashboard
- route spans include client id/role in v0.4

## Kubernetes architecture

The Helm chart defaults to two Gateway replicas sharing an external Redis backend.

```text
Ingress / Service
       |
   +---+---+
   |       |
Gateway  Gateway
   |       |
   +---+---+
       |
     Redis
```

Deployment controls include:

- liveness `/health`
- readiness `/ready`
- PodDisruptionBudget
- resource requests/limits
- non-root execution
- RuntimeDefault seccomp
- all Linux capabilities dropped
- read-only root filesystem
- optional HPA
- optional Ingress
- external Kubernetes Secret contract

## CI and release gate

```text
Ruff
Pytest
Redis integration
Docker build
Compose config
Helm lint
Helm template
   |
   +-- Security: secret scan rule + pip-audit
   |
   +-- Automatic semantic tag and GitHub Release
```
