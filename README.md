# Multi-LLM AI Gateway

> 企業級多模型 AI Gateway 範例 / Enterprise multi-provider AI gateway reference implementation.

A lightweight **OpenAI-compatible gateway** that provides one API surface for multiple LLM providers, with model routing, fallback, health checks, and request metadata.

## 功能 / Features

- **單一 API / Unified API**: `POST /v1/chat/completions`
- **多 Provider / Multi-provider**: OpenAI, Anthropic, Google Gemini, and Mock
- **模型路由 / Model routing**: explicit provider prefix or configured aliases
- **Fallback**: retry the same request against alternate providers/models
- **OpenAI-compatible response**: client applications only need one integration
- **Health & provider status**: `GET /health`, `GET /v1/providers`
- **Request ID**: every response includes `X-Request-ID`
- **Docker-ready**
- **CI**: Ruff + Pytest

## Architecture

```text
Client / Agent / RAG
        |
        v
+---------------------------+
|  Multi-LLM AI Gateway     |
|  FastAPI                  |
|                           |
|  OpenAI-compatible API    |
|       |                   |
|       v                   |
|  Router + Fallback        |
|   /       |       \       |
| OpenAI  Anthropic Gemini  |
+---------------------------+
        |
        v
 Provider APIs
```

## Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Or:

```bash
docker compose up --build
```

Then open:

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Providers: http://localhost:8000/v1/providers

## Example

```bash
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-gateway-key' \
  -d '{
    "model": "mock:demo",
    "messages": [
      {"role": "user", "content": "Hello gateway"}
    ]
  }'
```

The `mock` provider is built in so the repository can be tested without external credentials.

## Model naming

Use `provider:model`:

```text
openai:gpt-5
anthropic:claude-sonnet-4-5
google:gemini-2.5-pro
mock:demo
```

Aliases can be configured through `MODEL_ALIASES_JSON`.

## Configuration

See [docs/configuration.md](docs/configuration.md).

## Roadmap

- **v0.1** — unified chat API, adapters, routing, fallback, CI
- **v0.2** — policy routing, budgets, token/cost accounting, rate limits
- **v0.3** — Redis-backed distributed state, observability, metrics, tracing
- **v0.4** — admin console, provider/model governance, enterprise deployment examples

## 專案定位 / Project positioning

此專案適合作為企業 AI 平台的共用入口層，將 RAG、Agent、內部應用與不同 LLM Provider 解耦，讓模型切換、fallback、治理與成本控制可以集中處理。

This project demonstrates how an enterprise AI platform can decouple applications, RAG systems, and agents from individual LLM vendors through a centrally governed gateway.

## License

MIT
