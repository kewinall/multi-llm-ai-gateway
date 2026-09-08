# Streaming / 串流回應

v0.5 adds OpenAI-compatible Server-Sent Events (SSE) to:

```http
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "mock:demo",
  "stream": true,
  "messages": [{"role": "user", "content": "Hello"}]
}
```

Response:

```text
Content-Type: text/event-stream

data: {"object":"chat.completion.chunk",...}
data: {"object":"chat.completion.chunk",...}
data: [DONE]
```

## Provider behavior

| Provider | v0.5 stream mode |
|---|---|
| Mock | Native progressive chunks |
| OpenAI | Native upstream SSE |
| Anthropic | Gateway-normalized buffered stream |
| Google Gemini | Gateway-normalized buffered stream |

The common `BaseProvider.stream()` contract means provider-specific native streaming can be
introduced without changing the public Gateway API.

## Governance

Streaming requests pass through the same controls before the stream is opened:

1. Authentication / RBAC
2. Policy Engine
3. Rate limit
4. Budget
5. Routing / circuit state

A policy can deny streaming:

```json
{
  "effect": "allow",
  "roles": ["operator"],
  "models": ["mock:*"],
  "allow_stream": false
}
```

The request returns HTTP 403 before an SSE response is established.

## Usage and cost

When a provider emits usage metadata, the Gateway records prompt/completion tokens and cost after
stream completion. OpenAI native streaming requests include `stream_options.include_usage=true`.

If an upstream provider does not supply usage metadata, the completed request is still recorded,
but token/cost values may remain zero/unknown.
