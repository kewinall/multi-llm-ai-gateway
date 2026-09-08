# Changelog

All notable changes to this project are documented here.

## [0.3.0] - 2026-09-09

### Added

- Pluggable `memory` / `redis` state backend
- Redis-backed distributed sliding-window rate limiting
- Redis-backed round-robin cursor shared across Gateway replicas
- Redis-backed provider circuit-breaker state
- Redis-backed request/token/cost accounting
- Redis-backed daily/monthly budget counters
- Redis readiness checks through `GET /ready`
- Prometheus metrics through `GET /metrics`
- Request, token, cost, latency, provider-attempt, rate-limit, and budget metrics
- OpenTelemetry FastAPI and HTTPX instrumentation
- Explicit `llm.gateway.route` and `llm.provider.request` spans
- Docker Compose observability stack with Redis, Prometheus, Grafana, and OTel Collector
- Provisioned Grafana Prometheus datasource and AI Gateway dashboard
- Redis multi-client integration test proving distributed state sharing
- Automatic semantic Git tag and GitHub Release workflow
- Release quality gate with Redis integration tests and Docker build
- Release security gate with secret checks and `pip-audit`

### Changed

- Runtime governance APIs are asynchronous
- API keys are hashed before being used as rate-limit state identifiers
- `GET /health` now reports the active state backend
- Model metadata reports the active state backend

## [0.2.0] - 2026-09-09

### Added

- Policy routing: `priority`, `round_robin`, `random`, and `cost`
- Logical model pools through `MODEL_POOLS_JSON`
- Per-model token pricing through `MODEL_PRICING_JSON`
- In-memory token and USD usage accounting
- Daily and monthly budget enforcement
- Per-API-key sliding-window rate limiting
- Provider retry policy
- Provider circuit breaker with recovery window
- `GET /v1/models`, `GET /v1/usage`, and `GET /v1/budgets`
- Rich routing decision metadata including candidate order and attempts

## [0.1.0] - 2026-09-09

### Added

- OpenAI-compatible `POST /v1/chat/completions`
- OpenAI, Anthropic, Google Gemini, and local Mock provider adapters
- `provider:model` routing and JSON-configured model aliases
- Ordered fallback routing
- `GET /health` and authenticated `GET /v1/providers`
- API-key validation and request IDs
- Docker and Docker Compose runtime
- Pytest and Ruff CI checks
- Traditional Chinese / English documentation
