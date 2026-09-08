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

## OpenAI

Set `OPENAI_API_KEY`, then use a provider-qualified model:

```json
{
  "model": "openai:gpt-5",
  "messages": [{"role": "user", "content": "Summarize this document."}]
}
```

## Anthropic

Set `ANTHROPIC_API_KEY`:

```json
{
  "model": "anthropic:claude-sonnet-4-5",
  "messages": [{"role": "user", "content": "Review this architecture."}]
}
```

## Google Gemini

Set `GOOGLE_API_KEY`:

```json
{
  "model": "google:gemini-2.5-pro",
  "messages": [{"role": "user", "content": "Explain this dataset."}]
}
```

## Stable aliases

Applications should normally use logical aliases such as `default`, `fast`, or `quality`.
Administrators can then change the provider/model mapping without modifying client code.
