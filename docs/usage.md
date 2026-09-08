# 使用範例 / Usage

## Chat Completion

```bash
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-gateway-key' \
  -d '{
    "model": "mock:demo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Admin Console

Open:

```text
http://localhost:8000/admin
```

Development Admin Key:

```text
dev-admin-key
```

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

The response contains `api_key` once. Save it securely.

Use it:

```bash
curl http://localhost:8000/v1/models \
  -H 'X-API-Key: llmgw_<generated-key>'
```

## Dynamic alias

```bash
curl -X PUT http://localhost:8000/admin/api/aliases/quality \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{"target":"mock:quality"}'
```

The next request may immediately use:

```json
{
  "model": "quality",
  "messages": [{"role": "user", "content": "Use the managed alias"}]
}
```

## Dynamic model pool and cost routing

Create a pool:

```bash
curl -X PUT http://localhost:8000/admin/api/pools/balanced \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{"models":["mock:premium","mock:cheap"]}'
```

Set prices:

```bash
curl -X PUT http://localhost:8000/admin/api/pricing/mock:cheap \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{"input_per_million":1,"output_per_million":2}'
```

Then choose `cost` either per request or as the global runtime policy.

## Audit

```bash
curl http://localhost:8000/admin/api/audit \
  -H 'X-Admin-Key: dev-admin-key'
```

## RBAC behavior

- viewer: read APIs only
- operator: read + Chat Completion
- admin: operator + Admin API

## Usage / budget

```bash
curl http://localhost:8000/v1/usage -H 'X-API-Key: dev-gateway-key'
curl http://localhost:8000/v1/budgets -H 'X-API-Key: dev-gateway-key'
```

## Health / metrics

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics
```

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

## Helm

```bash
helm lint deploy/helm/multi-llm-ai-gateway
helm template ai-gateway deploy/helm/multi-llm-ai-gateway
```

See [Enterprise Deployment](enterprise-deployment.md) for the Kubernetes Secret contract and
installation example.
