# Multi-LLM AI Gateway

**目前版本：v0.5.0**

> **互動式架構與專案總覽**  
> [GitHub Pages](https://kewinall.github.io/multi-llm-ai-gateway/) · [Repository HTML](docs/multi-llm-ai-gateway-guide.html)

這是一套企業級 **Model Control Plane**，透過 centralized OpenAI-compatible Gateway 統一處理 multi-provider routing、resilience、streaming、policy、identity、quota / cost governance 與 observability。

## 專案定位

本 Repository 負責 Portfolio 中的 **Model Access and Governance Layer**：

- provider abstraction
- model routing 與 fallback
- retry 與 circuit breaker
- OpenAI-compatible streaming
- identity 與 RBAC
- request policy
- rate limiting
- token / cost accounting
- daily / monthly budget enforcement
- shared distributed governance state
- metrics、traces 與 audit events

本專案刻意不實作 RAG、MCP tool orchestration、ETL intelligence 或 DataOps reasoning。

## 架構

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
```

## 核心能力

- `POST /v1/chat/completions`
- OpenAI-compatible SSE streaming
- OpenAI、Anthropic、Google Gemini 與 Mock providers
- priority、round-robin、random、cost-aware routing
- retry、fallback、circuit breaker
- runtime aliases、pools、pricing 與 routing policy
- managed API clients 與 API-key rotation
- optional OIDC/JWT bearer authentication
- JWKS signature / issuer / audience / expiry validation
- RBAC：`viewer`、`operator`、`admin`
- Runtime Policy Engine
- daily / monthly budget enforcement
- Redis shared state，支援 multi-replica governance
- Prometheus、OpenTelemetry、Grafana integration
- Helm chart 與 Kubernetes hardening baseline

## 關鍵工程決策

| 決策 | 原因 / 效益 | Trade-off |
|---|---|---|
| Centralized Model Control Plane | 避免每個 AI application 重複實作 routing、identity、cost 與 policy | Gateway 成為重要 platform dependency |
| OpenAI-compatible contract | 降低 client / provider coupling | Provider-native feature 可能需要 normalization |
| Retry + fallback + circuit breaker | 降低 provider outage / 429 向上游擴散 | 增加 provider-specific test matrix |
| Redis shared governance state | 讓 replicas 間的 rate、budget、circuit state 保持一致 | Redis 成為 distributed-control dependency |
| Provider call 前執行 policy / budget gate | 在產生成本前拒絕不合規或超預算 request | Global policy 設定錯誤可能同時影響多個 client |

## 失敗語意與復原原則

- provider timeout / 429 / outage 可觸發 retry、fallback 與 circuit behavior
- invalid / expired OIDC credential 採 fail closed
- budget rejection 發生在 provider invocation 之前
- Redis unavailable 時，不再假設 cross-replica governance guarantee 仍然成立
- pod failure 透過 Kubernetes replicas / readiness / PDB 降低影響
- SSE stream 中斷時維持 incomplete，不可當作完整成功 response

## 可驗證 Evidence

| Claim | Repository Evidence |
|---|---|
| Routing / fallback regression | `tests/test_router.py` |
| Redis distributed state | `tests/test_redis_state.py` |
| Budget / policy / rate governance | `tests/test_governance.py`, `app/budget.py`, `app/policy.py`, `app/rate_limit.py` |
| OIDC / identity boundary | `tests/test_identity.py`, `app/security.py` |
| Kubernetes HA / hardening | `deploy/helm/multi-llm-ai-gateway/`, `.github/workflows/ci.yml` |
| Observability | `app/observability.py`, `docs/observability.md` |

## 快速開始

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

預設 local bootstrap credentials：

```text
X-API-Key:   dev-gateway-key
X-Admin-Key: dev-admin-key
```

Local surfaces：

| 介面 | URL |
|---|---|
| Swagger UI | `http://localhost:8000/docs` |
| Admin Console | `http://localhost:8000/admin` |
| Health | `http://localhost:8000/health` |
| Readiness | `http://localhost:8000/ready` |
| Metrics | `http://localhost:8000/metrics` |

## Streaming Request 範例

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

## Portfolio 責任邊界

- **Multi-LLM AI Gateway**：model routing、provider resilience、policy、identity、cost governance
- **Enterprise RAG Platform**：knowledge ingestion、retrieval、grounding、evaluation
- **Agentic DataOps Copilot**：operational reasoning 與 governed remediation
- **Data Platform MCP Server**：standardized data / tool integration contracts
- **Enterprise ETL Platform**：ETL modernization、metadata、lineage、runtime lifecycle

## 授權

MIT
