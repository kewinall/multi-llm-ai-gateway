# Multi-LLM AI Gateway

> 企業級多模型 AI Gateway 範例 / Enterprise multi-provider AI gateway reference implementation.

An **OpenAI-compatible AI Gateway** that decouples applications from LLM vendors and centralizes
routing, fallback, retries, cost governance, distributed state, metrics, and tracing.

## v0.3 Features

- **Unified API**: `POST /v1/chat/completions`
- **Providers**: OpenAI, Anthropic, Google Gemini, Mock
- **Routing**: priority, round-robin, random, cost-aware
- **Fallback, retry, circuit breaker**
- **Token / cost accounting and daily/monthly budgets**
- **Per-API-key sliding-window rate limiting**
- **Redis distributed state** for multi-replica deployments
- **Memory backend fallback** for local development and CI
- **Prometheus metrics** at `GET /metrics`
- **OpenTelemetry tracing** for FastAPI, HTTPX, gateway routing, and provider calls
- **Readiness probe** at `GET /ready`
- **Grafana dashboard provisioning**
- **Gated automatic GitHub Releases** after quality + security checks
- **CI Redis integration test** proving state sharing across independent clients

## Architecture

```text
                       +----------------------+
Client / Agent / RAG ->| Multi-LLM AI Gateway|
                       +----------+-----------+
                                  |
                   Auth -> Rate Limit -> Budget
                                  |
                    Model Pool / Policy Router
                     /        |         \
                  OpenAI   Anthropic   Gemini
                                  |
                         Usage / Cost
                                  |
                  +---------------+---------------+
                  |                               |
             Redis State                     Prometheus
       rate/budget/circuit/RR                  /metrics
                  |                               |
           Multi replicas                       Grafana
                                                  |
                                           AI Gateway Dashboard

Gateway + provider spans -> OpenTelemetry Collector
```

## Quick start — local Python

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Without `REDIS_URL`, `STATE_BACKEND=auto` selects the in-memory backend.

## Quick start — full observability stack

```bash
cp .env.example .env
docker compose up --build
```

Services:

| Service | URL |
|---|---|
| Gateway API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| OTLP/HTTP | http://localhost:4318 |

The Compose stack automatically runs the Gateway with Redis distributed state and OTLP tracing.

## API surface

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat request |
| `GET /v1/providers` | Provider configuration and circuit state |
| `GET /v1/models` | Aliases, pools, pricing, policy, backend |
| `GET /v1/usage` | Token/request/cost accounting |
| `GET /v1/budgets` | Daily/monthly budget status |
| `GET /health` | Process health |
| `GET /ready` | State backend readiness |
| `GET /metrics` | Prometheus metrics |

## Basic request

```bash
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-gateway-key' \
  -d '{
    "model": "mock:demo",
    "messages": [{"role": "user", "content": "Hello gateway"}]
  }'
```

## Distributed state

Set:

```dotenv
STATE_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
REDIS_PREFIX=llm-gateway
```

Redis stores shared rate-limit windows, round-robin cursor, circuit state, usage/cost counters,
daily/monthly budget state, and recent usage. Raw API keys are not used as Redis key names.

## Observability

Prometheus exports request count, token usage, estimated cost, provider attempts, latency,
rate-limit rejects, and budget rejects.

OpenTelemetry is enabled when:

```dotenv
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

The included Grafana provisioning creates an **AI Gateway** folder and dashboard automatically.

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Distributed state](docs/distributed-state.md)
- [Observability](docs/observability.md)
- [Usage examples](docs/usage.md)

## Release flow

```text
Version change
   |
   +-- Quality gate: Ruff + Pytest + Redis integration + Docker build
   |
   +-- Security gate: secret check + pip-audit
   |
   +-- GitHub Actions creates semantic tag + GitHub Release
```

## Roadmap

- **v0.1** — unified chat API, adapters, routing, fallback, CI
- **v0.2** — policy routing, retries, circuit breaker, budgets, cost accounting, rate limits
- **v0.3** — Redis distributed state, Prometheus, OpenTelemetry, Grafana, release gates
- **v0.4** — admin console, provider/model governance, enterprise deployment examples

## 專案定位 / Project positioning

此專案展示企業 AI 平台如何將 RAG、Agent、內部應用與個別 LLM Provider 解耦，並集中
**Model Routing、Resilience、Cost Governance、Distributed State、Observability**。

## License

MIT
