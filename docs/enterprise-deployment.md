# Enterprise Deployment / 企業部署

v0.5 Helm chart:

```text
deploy/helm/multi-llm-ai-gateway
```

## Secret contract

Create the referenced Secret before install:

```bash
kubectl create secret generic multi-llm-ai-gateway-secrets \
  --from-literal=gateway-api-key='<gateway-key>' \
  --from-literal=admin-api-key='<admin-key>' \
  --from-literal=redis-url='rediss://redis.example.internal:6379/0'
```

Optional provider keys:

```text
openai-api-key
anthropic-api-key
google-api-key
```

OIDC settings are non-secret and configured through Helm values.

## Install

```bash
helm upgrade --install ai-gateway \
  deploy/helm/multi-llm-ai-gateway \
  --set image.repository=<registry>/multi-llm-ai-gateway \
  --set image.tag=0.5.0 \
  --set config.oidcIssuer=https://id.example.com/ \
  --set config.oidcAudience=ai-gateway \
  --set config.oidcJwksUrl=https://id.example.com/.well-known/jwks.json
```

## Hardened pod defaults

- replicas: 2
- `runAsNonRoot: true`
- `runAsUser: 10001`
- `runAsGroup: 10001`
- `fsGroup: 10001`
- RuntimeDefault seccomp
- `allowPrivilegeEscalation: false`
- all capabilities dropped
- read-only root filesystem
- service account token automount disabled
- CPU/memory requests and limits
- PodDisruptionBudget
- liveness/readiness probes

## NetworkPolicy

Disabled by default because enterprise networks differ.

Enable:

```bash
--set networkPolicy.enabled=true
```

The reference policy permits:

- inbound Gateway HTTP port from the configured namespace selector
- DNS TCP/UDP 53
- Redis TCP port
- HTTPS TCP 443

Treat this as a baseline. Narrow egress destinations and ingress namespace/pod selectors for the
actual platform.

## Prometheus ServiceMonitor

If Prometheus Operator is installed:

```bash
--set serviceMonitor.enabled=true
```

The ServiceMonitor scrapes the Gateway Service `http` port at `/metrics`.

## HPA / Ingress

Both remain optional:

```yaml
autoscaling:
  enabled: true

ingress:
  enabled: true
```

## Production dependencies

Recommended:

- managed Redis or HA Redis
- Redis TLS/authentication
- external secret manager
- TLS ingress
- enterprise OIDC provider
- Prometheus/Grafana or equivalent monitoring
- OpenTelemetry collector/backend
- image scanning/signing
- namespace/network isolation
- log and audit retention
