# Changelog

All notable changes to this project are documented here.

## [0.5.0] - 2026-09-09

### Added

- OpenAI-compatible SSE streaming on `POST /v1/chat/completions`
- Native progressive Mock streaming
- Native OpenAI upstream SSE normalization
- Common provider stream contract with buffered normalization fallback
- Optional OIDC/JWT bearer authentication
- JWKS-backed JWT signature validation
- Issuer, audience, `exp`, `iat`, and `sub` validation
- Configurable OIDC role/name claims
- Request Policy Engine
- Policy matching by role, principal ID, model glob, streaming mode, and max tokens
- Runtime policy CRUD through Admin API
- Redis-backed policies shared across replicas
- Managed client API-key rotation
- Immediate invalidation of previous API key after rotation
- Rotation audit events
- Policy rejection Prometheus metric
- Request Policy management in Admin Console
- API key rotation action in Admin Console
- Optional Helm NetworkPolicy
- Optional Prometheus Operator ServiceMonitor
- Hardened fixed non-root UID/GID
- Disabled service account token automount
- Helm CI rendering for optional hardening resources
- OIDC/JWT validation tests
- FastAPI bearer-auth integration test
- Redis distributed policy and rotation integration tests
- SSE chunk reconstruction and post-stream usage accounting test

### Changed

- Chat requests now pass through Policy Engine before rate/budget/routing
- Chat metadata includes authentication source
- Streaming requests use the same RBAC, policy, rate, budget, circuit, usage, and cost governance
- Helm image/app version updated to 0.5.0

## [0.4.0] - 2026-09-09

### Added

- Embedded Admin Console
- Dynamic Redis-backed runtime governance
- Managed API clients
- viewer/operator/admin RBAC
- Per-client rate limits
- Audit log
- Helm/Kubernetes deployment

## [0.3.0] - 2026-09-09

### Added

- Redis distributed runtime state
- Prometheus metrics
- OpenTelemetry tracing
- Grafana provisioning
- Automatic semantic GitHub Releases

## [0.2.0] - 2026-09-09

### Added

- Routing policies
- Model pools
- Pricing
- Retry/fallback/circuit breaker
- Budgets and rate limiting

## [0.1.0] - 2026-09-09

### Added

- OpenAI-compatible Chat Completion API
- OpenAI, Anthropic, Google Gemini, and Mock providers
- Alias/fallback routing
- Docker and CI
