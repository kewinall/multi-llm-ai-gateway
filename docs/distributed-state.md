# 分散式狀態 / Distributed State

v0.3 introduces a state backend abstraction so multiple Gateway replicas can share governance state.

## Backend selection

```dotenv
STATE_BACKEND=auto
REDIS_URL=redis://redis:6379/0
REDIS_PREFIX=llm-gateway
```

Modes:

| Mode | Behavior |
|---|---|
| `auto` | Redis when `REDIS_URL` exists; otherwise memory |
| `memory` | Always process-local memory |
| `redis` | Require Redis; startup configuration fails without `REDIS_URL` |

## Shared state

When Redis is active, the following are distributed across replicas:

- per-API-key sliding-window rate limits
- round-robin cursor
- provider circuit-breaker state
- total/model token usage
- estimated USD cost
- daily/monthly budget counters
- recent usage records

## Why API keys are not stored directly

Rate-limit principals are SHA-256-derived identifiers before being used as state keys. This prevents raw gateway API keys from being embedded in Redis key names.

## Redis data model

Conceptually:

```text
llm-gateway:rate:<principal>                 ZSET
llm-gateway:round-robin:<pool>               counter
llm-gateway:circuit:<provider>               HASH
llm-gateway:usage:totals                     HASH
llm-gateway:usage:model:<provider:model>     HASH
llm-gateway:usage:cost:day:<yyyy-mm-dd>      string/float
llm-gateway:usage:cost:month:<yyyy-mm>       string/float
llm-gateway:usage:recent                     LIST
llm-gateway:usage:models                     SET
```

## Multi-replica behavior

The CI integration test creates two independent Redis clients using the same prefix and verifies that state written by one client is immediately visible to the other. This explicitly covers the distributed behavior expected from multiple Gateway replicas.

## Failure behavior

`GET /ready` checks the selected backend. With Redis configured, Redis connectivity failure returns HTTP 503 so Kubernetes/Ingress readiness probes can stop sending new requests to an unhealthy replica.
