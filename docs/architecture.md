# 架構設計 / Architecture

## 目標 / Goal

讓 Agent、RAG、Web 應用與批次工作只整合一種 Chat Completion API，而不需要直接依賴
OpenAI、Anthropic 或 Google 的個別 API 格式。

Expose one stable Chat Completion API so applications can switch providers without changing client
integration code.

## Request flow

```text
1. Client sends OpenAI-style request
2. Gateway validates X-API-Key
3. ModelRouter resolves alias or provider:model
4. Provider adapter transforms the request
5. Upstream result is normalized to OpenAI-style response
6. On provider failure, configured fallback candidates are tried
7. Gateway route metadata and X-Request-ID are returned
```

## Components

```text
app/main.py
  |
  +-- security.py
  |
  +-- router.py
        |
        +-- providers/openai.py
        +-- providers/anthropic.py
        +-- providers/google.py
        +-- providers/mock.py
```

## Design decisions

### Provider abstraction

Each adapter implements the same `BaseProvider` contract. Vendor-specific request/response formats
remain outside the application-facing API.

### Explicit model namespace

`provider:model` prevents naming collisions and makes routing decisions auditable. Aliases allow
stable logical names such as `default`, `fast`, or `quality`.

### Controlled fallback

Only expected gateway/provider errors trigger fallback. Unexpected programming errors propagate
instead of being silently masked.

### Mock provider

The local mock adapter gives CI and developers a deterministic, credential-free end-to-end path.

## v0.1 limitations

- Non-streaming requests only
- No distributed rate limiting
- No token/cost budget policy
- No Redis state
- No Prometheus/OpenTelemetry integration
- Basic API-key authentication only

These are intentionally deferred to later roadmap versions.
