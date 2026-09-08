# 架構設計 / Architecture

## 目標 / Goal

v0.3 將 Gateway 從單 process governance reference implementation 提升為可支援多 replica
的分散式架構，並加入 metrics、trace 與 readiness。

## Request flow

```text
Client
  |
  v
FastAPI + request/trace context
  |
  v
API key authentication
  |
  v
Distributed Rate Limit ------> HTTP 429
  |
  v
Distributed Budget ----------> HTTP 429
  |
  v
Model Pool / Routing Policy
  |  priority / round_robin / random / cost
  v
Distributed Circuit Breaker
  |
  v
Provider Retry / Fallback
  |
  +---- OpenAI
  +---- Anthropic
  +---- Google Gemini
  +---- Mock
  |
  v
Usage + Pricing
  |
  +---- Redis: usage / cost / budget state
  |
  +---- Prometheus: metrics
  |
  +---- OpenTelemetry: spans
  |
  v
OpenAI-compatible response
```

## State backend abstraction

```text
                       StateBackend
                      /            \
          InMemoryStateBackend    RedisStateBackend
                 |                       |
             local demo             multi replica
             unit tests             distributed
```

The same RateLimiter, BudgetManager, UsageStore, CircuitBreaker, and ModelRouter consume this
interface. Application logic does not need separate Redis-specific code paths.

## Redis state

Redis provides shared state for:

- sliding-window rate limiting
- round-robin cursor
- circuit breaker
- total/model usage
- daily/monthly cost
- budget evaluation
- recent usage

Rate-limit identities are hashed before becoming Redis keys.

## Observability

### Prometheus

`/metrics` exports request, latency, token, cost, provider-attempt and rejection metrics.

### OpenTelemetry

When an OTLP endpoint is configured:

- FastAPI inbound requests are instrumented
- HTTPX outbound LLM calls are instrumented
- `llm.gateway.route` captures route decisions
- `llm.provider.request` captures provider/model/retry attributes

### Grafana

The reference Compose deployment provisions a Prometheus datasource and AI Gateway dashboard.

## Health model

| Endpoint | Meaning |
|---|---|
| `/health` | Application process is alive |
| `/ready` | Selected state backend is available |
| `/metrics` | Prometheus scrape endpoint |

This separation lets orchestrators remove a replica from traffic when Redis is unavailable without
treating the process itself as dead.

## CI and release gate

```text
main / version change
      |
      +--> CI: Ruff + Pytest + Redis integration + Docker build
      |
      +--> Release quality gate
      |
      +--> Release security gate: local-secret check + pip-audit
                    |
                    v
              Git tag + Release
```

The Redis integration test uses two separate Redis clients with one shared prefix to verify
distributed state visibility explicitly.
