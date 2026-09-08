# 使用範例 / Usage

## Buffered Chat Completion

```bash
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-gateway-key' \
  -d '{
    "model": "mock:demo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## SSE Streaming

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-gateway-key' \
  -d '{
    "model": "mock:demo",
    "stream": true,
    "messages": [{"role": "user", "content": "Hello stream"}]
  }'
```

Response terminates with:

```text
data: [DONE]
```

## OIDC bearer request

After OIDC configuration:

```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer $TOKEN"
```

Mapped operator/admin identities may invoke Chat Completion.

## Create a managed client

```bash
curl -X POST http://localhost:8000/admin/api/clients \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "name":"rag-service",
    "role":"operator",
    "rate_limit_requests_per_minute":30
  }'
```

The `api_key` field is shown once.

## Rotate client key

```bash
curl -X POST \
  http://localhost:8000/admin/api/clients/<client-id>/rotate-key \
  -H 'X-Admin-Key: dev-admin-key'
```

The old key stops authenticating immediately.

## Create request policy

Deny a model family:

```bash
curl -X PUT http://localhost:8000/admin/api/policies/block-secret \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "priority":1,
    "effect":"deny",
    "models":["mock:secret*"]
  }'
```

Limit output tokens:

```bash
curl -X PUT http://localhost:8000/admin/api/policies/operator-limit \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "priority":10,
    "effect":"allow",
    "roles":["operator"],
    "max_tokens":2048
  }'
```

## Dynamic alias

```bash
curl -X PUT http://localhost:8000/admin/api/aliases/quality \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{"target":"mock:quality"}'
```

## Audit

```bash
curl http://localhost:8000/admin/api/audit \
  -H 'X-Admin-Key: dev-admin-key'
```

## Health / metrics

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics
```

## Helm validation

```bash
helm lint deploy/helm/multi-llm-ai-gateway

helm template ai-gateway deploy/helm/multi-llm-ai-gateway

helm template ai-gateway-hardening deploy/helm/multi-llm-ai-gateway \
  --set networkPolicy.enabled=true \
  --set serviceMonitor.enabled=true
```
