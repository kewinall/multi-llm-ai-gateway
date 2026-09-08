# 使用範例 / Usage

## Mock provider

```bash
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-gateway-key' \
  -d '{
    "model": "mock:demo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Provider-qualified models

```json
{"model":"openai:gpt-5","messages":[{"role":"user","content":"Summarize this."}]}
```

```json
{"model":"anthropic:claude-sonnet-4-5","messages":[{"role":"user","content":"Review this."}]}
```

```json
{"model":"google:gemini-2.5-pro","messages":[{"role":"user","content":"Explain this."}]}
```

Configure the corresponding Provider API key before using external models.

## Policy routing

```json
{
  "model": "balanced",
  "routing_policy": "round_robin",
  "messages": [{"role": "user", "content": "Route me"}]
}
```

With Redis enabled, the round-robin cursor is shared by all Gateway replicas.

## Usage and budget

```bash
curl http://localhost:8000/v1/usage -H 'X-API-Key: dev-gateway-key'
curl http://localhost:8000/v1/budgets -H 'X-API-Key: dev-gateway-key'
```

The usage response includes `backend: memory|redis`.

## Health and readiness

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

With Redis selected, `/ready` returns HTTP 503 if the Redis backend cannot be reached.

## Prometheus

```bash
curl http://localhost:8000/metrics
```

## Full stack

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Gateway: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

The included Compose file configures the Gateway to use Redis and send OTLP/HTTP traces to the
OpenTelemetry Collector.
