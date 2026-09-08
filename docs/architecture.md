# 架構設計 / Architecture

## v0.5 goal

v0.5 extends the management/data-plane architecture with enterprise identity, runtime request
policy, SSE streaming, key rotation, and Kubernetes network/monitoring hardening.

## Request path

```text
                    Authentication
          +-------------+-------------+
          |                           |
      X-API-Key                  Bearer JWT
          |                           |
 managed/bootstrap key          OIDC + JWKS
          +-------------+-------------+
                        |
                     Principal
               id / name / role / source
                        |
                        v
                   Policy Engine
                        |
             +----------+----------+
             |                     |
          DENY 403                ALLOW
                                   |
                              Rate Limit
                                   |
                                Budget
                                   |
                         Governance Snapshot
                                   |
                              Model Router
                      priority / RR / random / cost
                                   |
                         Circuit / retry / fallback
                                   |
                              Provider
                                   |
                    +--------------+--------------+
                    |                             |
                Buffered                         SSE
                    |                             |
                    +--------------+--------------+
                                   |
                            Usage / Cost
                                   |
                        Metrics / Trace / Audit
```

## Identity

Supported identity sources:

- bootstrap `ADMIN_API_KEY`
- bootstrap `GATEWAY_API_KEY`
- managed hashed API client key
- OIDC bearer JWT

OIDC token validation uses configured JWKS and verifies issuer, audience, expiry, issue time, and
subject. Role mapping converts the configured claim to viewer/operator/admin.

## Policy Engine

Policies are part of the same effective Governance Snapshot as aliases, pools, pricing, and routing
settings.

```text
Environment POLICIES_JSON
          +
Redis/memory policy overrides
          =
Effective policies
```

Policies are ordered by ascending priority. The first matching rule evaluates:

- role
- principal ID
- requested model glob
- streaming allowed/denied
- maximum requested output tokens
- allow/deny effect

Default behavior remains allow for backward compatibility.

## Streaming architecture

```text
ChatCompletionRequest(stream=true)
        |
Policy / Rate / Budget
        |
Router.stream_route()
        |
BaseProvider.stream()
   |           |
 native       normalized buffered fallback
   |
OpenAI / Mock
        |
SSE chunk normalization
        |
Usage/cost finalization
        |
data: [DONE]
```

Native OpenAI streaming asks the upstream API to include usage. Mock streaming is deterministic and
progressive for CI. Anthropic/Google currently inherit normalized buffered streaming from the common
provider contract.

## Distributed governance

Redis stores:

```text
rate-limit windows
round-robin state
circuit state
usage / cost
budget counters
dynamic aliases
model pools
pricing
routing policy
request policies
managed client key digests
audit events
```

Key rotation atomically creates a new digest, deletes the old digest, and preserves the logical
client ID.

## Kubernetes

```text
Ingress / Gateway API
        |
     Service
        |
 +------+------+ 
 |             |
Pod A         Pod B
 |             |
 +------+------+ 
        |
      Redis

Optional:
- NetworkPolicy
- ServiceMonitor
- HPA
- Ingress
```

Pod hardening:

- non-root UID/GID 10001
- RuntimeDefault seccomp
- no privilege escalation
- all capabilities dropped
- read-only root filesystem
- service account token automount disabled
- resource limits
- PDB

## Observability

Prometheus includes:

- request/token/cost/provider-attempt metrics
- latency
- rate-limit rejection
- budget rejection
- policy rejection

OpenTelemetry continues to trace FastAPI, HTTPX, route and provider operations.

## Release gate

```text
Ruff
Pytest
Redis integration
Docker build
Compose config
Helm lint
Helm normal render
Helm NetworkPolicy + ServiceMonitor render
     |
Security: secret rule + pip-audit
     |
semantic tag + GitHub Release
```
