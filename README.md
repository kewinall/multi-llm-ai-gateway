# Multi-LLM AI Gateway

> 企業級多模型 AI Gateway 範例 / Enterprise multi-provider AI gateway reference implementation.

An **OpenAI-compatible AI Gateway** that decouples applications from LLM vendors and centralizes
routing, fallback, retries, cost accounting, budgets, rate limits, and provider resilience.

## v0.2 Features

- **Unified API**: `POST /v1/chat/completions`
- **Providers**: OpenAI, Anthropic, Google Gemini, Mock
- **Logical aliases and model pools**
- **Routing policies**: priority, round-robin, random, cost-aware
- **Fallback + provider retry**
- **Circuit breaker**
- **Token / cost accounting**
- **Daily / monthly budget enforcement**
- **Per-API-key rate limiting**
- **Governance APIs**: models, providers, usage, budgets
- **Request ID + detailed routing metadata**
- **Docker-ready**
- **CI**: Ruff + Pytest + Docker build

## Architecture

```text
Client / Agent / RAG
        |
        v
+----------------------------------+
| Multi-LLM AI Gateway             |
|                                  |
| Auth -> Rate Limit -> Budget     |
|                |                 |
|                v                 |
|      Model Pool / Policy Router  |
| priority | RR | random | cost    |
|                |                 |
|        Retry + Circuit Breaker   |
|         /       |       \        |
|     OpenAI  Anthropic  Gemini    |
|                |                 |
|                v                 |
|      Usage / Cost Accounting     |
+----------------------------------+
```

## Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Or:

```bash
docker compose up --build
```

Then:

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Providers: http://localhost:8000/v1/providers
- Models: http://localhost:8000/v1/models
- Usage: http://localhost:8000/v1/usage
- Budgets: http://localhost:8000/v1/budgets

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

## Policy routing example

Configure a model pool:

```dotenv
MODEL_POOLS_JSON={"balanced":["mock:primary","mock:secondary"]}
MODEL_PRICING_JSON={"mock:primary":{"input_per_million":2,"output_per_million":4},"mock:secondary":{"input_per_million":1,"output_per_million":2}}
```

Then request cost-aware routing:

```json
{
  "model": "balanced",
  "routing_policy": "cost",
  "messages": [{"role": "user", "content": "Route this request"}]
}
```

The response includes a `gateway` object with the selected provider/model, candidate ordering,
retry attempts, fallback state, request cost, and budget status.

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Usage examples](docs/usage.md)

## Roadmap

- **v0.1** — unified chat API, adapters, routing, fallback, CI
- **v0.2** — policy routing, retries, circuit breaker, budgets, token/cost accounting, rate limits
- **v0.3** — Redis-backed distributed state, observability, metrics, tracing
- **v0.4** — admin console, provider/model governance, enterprise deployment examples

## 專案定位 / Project positioning

此專案展示企業 AI 平台如何將 RAG、Agent、內部應用與個別 LLM Provider 解耦，並把
**Model Routing、Resilience、Cost Governance** 集中到共用 Gateway。

v0.2 的治理狀態目前採 in-memory 實作；這是刻意保留給 v0.3 Redis distributed state
升級的架構邊界。

## License

MIT
