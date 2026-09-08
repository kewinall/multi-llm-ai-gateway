# Changelog

All notable changes to this project are documented here.

## [0.4.0] - 2026-09-09

### Added

- Embedded Admin Console at `GET /admin`
- Runtime Admin API for aliases, pools, pricing, routing policy, clients, and audit events
- Dynamic governance store for memory and Redis backends
- Redis-backed governance shared across Gateway replicas
- Managed API client creation, update, disable, and deletion
- API keys generated with `llmgw_` prefix and stored as SHA-256 digests only
- RBAC roles: `viewer`, `operator`, and `admin`
- Bootstrap `ADMIN_API_KEY` administrator credential
- Backward-compatible `GATEWAY_API_KEY` bootstrap operator
- Per-client requests-per-minute override
- Governance audit log
- Dynamic cost routing and pricing without application restart
- Helm chart for Kubernetes deployment
- Default two-replica deployment
- Liveness/readiness probes, PodDisruptionBudget, hardened security context, and resource limits
- Optional HPA and Ingress
- Helm lint/template validation in CI and Release quality gates
- Redis integration coverage for shared governance, managed clients, and audit state

### Changed

- Router reads the effective governance snapshot at request time
- Cost calculation uses dynamically governed pricing
- Chat response includes authenticated client identity metadata
- OpenTelemetry route span records client id and role

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
- OpenTelemetry FastAPI and HTTPX instrumentation
- Docker Compose observability stack with Redis, Prometheus, Grafana, and OTel Collector
- Automatic semantic Git tag and GitHub Release workflow
- Release security gate with secret checks and `pip-audit`

## [0.2.0] - 2026-09-09

### Added

- Policy routing: `priority`, `round_robin`, `random`, and `cost`
- Logical model pools
- Per-model token pricing
- Token and USD usage accounting
- Daily/monthly budget enforcement
- Sliding-window rate limiting
- Provider retries and circuit breaker

## [0.1.0] - 2026-09-09

### Added

- OpenAI-compatible `POST /v1/chat/completions`
- OpenAI, Anthropic, Google Gemini, and Mock adapters
- Model aliases and ordered fallback
- API-key validation and request IDs
- Docker runtime
- Pytest and Ruff CI
