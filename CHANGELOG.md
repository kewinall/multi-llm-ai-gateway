# Changelog

All notable changes to this project are documented here.

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
- Governance tests for routing, budgets, rate limits, and circuit state

### Notes

v0.2 intentionally keeps runtime governance state in memory. Distributed state is planned for v0.3.

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
