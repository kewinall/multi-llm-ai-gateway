# Multi-LLM AI Gateway

**Current release: v0.5.0**

> **Interactive architecture & project overview**  
> [Live GitHub Pages](https://kewinall.github.io/multi-llm-ai-gateway/) · [Repository HTML](docs/multi-llm-ai-gateway-guide.html)

Enterprise **Model Control Plane** providing a centralized OpenAI-compatible gateway for multi-provider routing, resilience, streaming, policy, identity, quota/cost governance, and observability.

## Engineering Scope

This repository owns the **model access and governance layer**:

- provider abstraction
- model routing and fallback
- retry and circuit breaking
- OpenAI-compatible streaming
- identity and RBAC
- request policy
- rate limiting
- token / cost accounting
- daily and monthly budget enforcement
- shared distributed governance state
- metrics, traces and audit events

It intentionally does not implement RAG, MCP tool orchestration, ETL intelligence, or DataOps reasoning.

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
```

## Core Capabilities

- `POST /v1/chat/completions`
- OpenAI-compatible SSE streaming
- OpenAI, Anthropic, Google Gemini and Mock providers
- priority, round-robin, random and cost-aware routing
- retry, fallback and circuit breaker
- runtime aliases, pools, pricing and routing policy
- managed API clients and API-key rotation
- optional OIDC/JWT bearer authentication
- JWKS signature / issuer / audience / expiry validation
- RBAC: `viewer`, `operator`, `admin`
- Runtime Policy Engine
- daily/monthly budget enforcement
- Redis shared state for multi-replica governance
- Prometheus, OpenTelemetry and Grafana integration
- Helm chart and Kubernetes hardening baseline

## Key Engineering Decisions

| Decision | Rationale | Trade-off |
|---|---|---|
| Centralized model control plane | Avoids duplicating routing, identity, cost and policy logic in every AI application | Gateway becomes a critical platform dependency |
| OpenAI-compatible contract | Reduces client/provider coupling | Provider-native features may require normalization |
| Retry + fallback + circuit breaker | Limits propagation of provider outage / 429 failures | Expands provider-specific test matrix |
| Redis shared governance state | Keeps rate, budget and circuit state coherent across replicas | Redis becomes a distributed-control dependency |
| Policy / budget before provider call | Rejects non-compliant or over-budget requests before cost is incurred | Misconfigured global policy can affect many clients |

## Failure Semantics

- provider timeout / 429 / outage can trigger retry, fallback and circuit behavior
- invalid or expired OIDC credentials fail closed
- budget rejection occurs before provider invocation
- Redis loss means cross-replica governance guarantees can no longer be assumed
- pod failures are handled through Kubernetes replicas/readiness/PDB
- interrupted SSE streams remain incomplete and must not be treated as successful full responses

## Production Evidence

| Claim | Repository Evidence |
|---|---|
| Routing / fallback regression | `tests/test_router.py` |
| Redis distributed state | `tests/test_redis_state.py` |
| Budget / policy / rate governance | `tests/test_governance.py`, `app/budget.py`, `app/policy.py`, `app/rate_limit.py` |
| OIDC / identity boundary | `tests/test_identity.py`, `app/security.py` |
| Kubernetes HA / hardening | `deploy/helm/multi-llm-ai-gateway/`, `.github/workflows/ci.yml` |
| Observability | `app/observability.py`, `docs/observability.md` |

## Quick Start

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

Local surfaces:

| Surface | URL |
|---|---|
| Swagger UI | `http://localhost:8000/docs` |
| Admin Console | `http://localhost:8000/admin` |
| Health | `http://localhost:8000/health` |
| Readiness | `http://localhost:8000/ready` |
| Metrics | `http://localhost:8000/metrics` |

## Example Streaming Request

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

## Portfolio Boundary

- **Multi-LLM AI Gateway:** model routing, provider resilience, policy, identity and cost governance
- **Enterprise RAG Platform:** knowledge ingestion, retrieval, grounding and evaluation
- **Agentic DataOps Copilot:** operational reasoning and governed remediation
- **Data Platform MCP Server:** standardized data/tool integration contracts
- **Enterprise ETL Platform:** ETL modernization, metadata, lineage and runtime lifecycle

## License

MIT
