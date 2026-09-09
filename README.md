# Multi-LLM AI Gateway

**目前版本 / Current release: v0.5.0**

> **📘 Interactive Project Guide / 專案互動式說明文件**  
> [Open Live Project Guide](https://kewinall.github.io/multi-llm-ai-gateway/) · [Repository HTML](docs/multi-llm-ai-gateway-guide.html) — 架構、Request Lifecycle、Multi-LLM Routing、Streaming、OIDC/RBAC、Policy、Cost Governance、Observability、Kubernetes/Helm、CI/Security、版本演進與面試官速讀集中於單一自包含 HTML。

> **繁體中文**：企業級 **Model Control Plane**，集中處理 Multi-LLM Routing、Fallback、Streaming、Policy、Quota/Cost、Identity 與 Observability。
>
> **English**: An enterprise **Model Control Plane** for centralized multi-provider routing, fallback, streaming, policy enforcement, quota/cost governance, identity, and observability.

An **OpenAI-compatible Enterprise AI Gateway** that decouples applications from LLM vendors. It intentionally does not implement RAG, MCP tool orchestration, or DataOps reasoning; those responsibilities belong to other portfolio layers.

## Portfolio Role / 作品集角色

**Primary role: Model Control Plane / 模型控制平面**

此 Repository 主要回答：**多個 RAG / Agent / Application 如何透過單一 OpenAI-compatible 入口，使用不同模型供應商，同時受到 Routing、Fallback、Policy、Budget 與 Observability 的集中治理？**  
This repository primarily answers: **How can multiple applications and agents consume heterogeneous LLM providers through one governed control plane?**

Portfolio responsibility boundary:

- **This repository:** model routing, provider abstraction, resilience, streaming, policy, identity, budget/cost, distributed gateway state, observability.
- [Enterprise RAG Platform](https://github.com/kewinall/enterprise-rag-platform): enterprise knowledge ingestion, retrieval, grounding, citations, and evaluation.
- [Agentic DataOps Copilot](https://github.com/kewinall/agentic-dataops-copilot): incident reasoning and governed DataOps operations.
- [Data Platform MCP Server](https://github.com/kewinall/data-platform-mcp-server): standardized MCP tool and data-platform integration layer.

**Intentional scope boundary:** no vector database, document ingestion, RAG pipeline, MCP server, or agent orchestration is added here.

## Engineering Decisions & Production Evidence

### Problem

如果每個 Application / RAG / Agent 都直接整合 OpenAI、Anthropic、Gemini 或其他 provider，**identity、routing、fallback、rate limit、budget、cost、policy、audit 與 observability** 會被複製到每個應用。這不只增加維護成本，也讓 provider outage 或 cost spike 難以集中控制。

### Key Engineering Decisions & Trade-offs

| Decision | Why / Benefit | Trade-off |
|---|---|---|
| **Centralized Model Control Plane** | 將 provider selection、resilience、policy、cost 與 observability 集中治理 | Gateway 本身成為新的 critical path，需要 HA、capacity 與 operational ownership |
| **OpenAI-compatible client contract** | 上游 application 可降低 provider coupling，切換 routing 不需要大量改 client | Provider-specific advanced capability 可能需要 normalization 或無法 1:1 暴露 |
| **Routing + Retry + Fallback + Circuit Breaker** | 單一 provider outage / 429 不必直接擴散到所有 client | 多 provider 行為差異會增加 error normalization、streaming 與 test matrix |
| **Redis shared governance state** | Multi-replica 之間共享 rate limit、round-robin cursor、circuit、usage/budget state | Redis 成為 distributed control dependency，需要 HA 與 failure semantics |
| **Policy / Budget 在 provider call 之前 gate** | 不合規或超預算 request 在產生成本前就被拒絕 | Policy / pricing / quota configuration 錯誤會影響所有 clients，需嚴格 change control |

### Production Failure & Recovery

| Scenario | Engineering Behavior / Detection | Recovery Strategy |
|---|---|---|
| Provider timeout / 429 / outage | Retry / fallback / circuit breaker 防止單一 provider failure 直接擴散 | 由 router 選擇可用 provider；恢復後 circuit state 再納回 routing |
| Budget exceeded | Request 在 provider call 前被 budget gate 拒絕 | 調整 budget / pricing / client policy，或等待 budget window reset |
| Invalid / expired OIDC JWT | Identity gate 拒絕 request，不應 fallback 成 anonymous privileged access | 更新 token / IdP configuration；維持 fail-closed |
| Redis unavailable | Cross-replica governance guarantee 不再可信，應視為 distributed control dependency incident | 恢復 Redis/HA backend；在恢復前不要假設 rate/budget/circuit state 跨 replicas 一致 |
| Gateway pod failure | Kubernetes readiness / replicas / PDB 降低單 pod failure 影響 | 由 Service 導向健康 replica，修復或重新排程失敗 pod |
| SSE stream 中斷 | Client 可觀察 incomplete stream；Gateway 必須保持 provider/request evidence 可追蹤 | 根據 idempotency / application semantics 決定重試，不把 partial response 當 complete |

### Production Evidence

| Claim | Repository Evidence |
|---|---|
| Routing / fallback behavior 有 regression tests | `tests/test_router.py` |
| Redis distributed state 有 integration tests | `tests/test_redis_state.py` |
| Budget / policy / runtime governance 有測試 | `tests/test_governance.py`, `app/budget.py`, `app/policy.py`, `app/rate_limit.py` |
| OIDC / identity boundary 有測試 | `tests/test_identity.py`, `app/security.py` |
| Kubernetes HA / hardening baseline | `deploy/helm/multi-llm-ai-gateway/`, `.github/workflows/ci.yml` |
| Observability implementation | `app/observability.py`, `docs/observability.md` |

### Interview Questions This Project Can Answer

- 為什麼 application 不直接 call provider API？
- Gateway 變成 critical path，怎麼避免它成為新的單點？
- Redis 掛掉時，哪些 guarantee 會失效？
- Cost-aware routing 與品質 / latency routing 之間如何取捨？
- OpenAI-compatible abstraction 會犧牲哪些 provider-native capability？


## Reference Integration / 參考整合

    Enterprise RAG Platform --------+
                                    |
    Agentic DataOps Copilot --------+--> Multi-LLM AI Gateway
                                    |          |
    Other AI Applications ----------+          +--> OpenAI
                                               +--> Anthropic
                                               +--> Gemini
                                               +--> Local / Other

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

- [Interactive Project Guide / 專案互動式說明文件](docs/multi-llm-ai-gateway-guide.html)
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
- **v0.6** — deeper provider-native streaming, external policy/identity integration, HA operations while remaining strictly focused on the model-control plane

## 專案定位 / Project positioning

此專案展示企業 AI Platform 如何集中處理 **Model Routing、Streaming、Resilience、
Cost Governance、OIDC/JWT、RBAC、Policy Enforcement、Distributed Governance、
Observability 與 Kubernetes Production Deployment**。

## License

MIT
