# 設定說明 / Configuration

本專案以環境變數設定 Gateway 與各 LLM Provider。正式環境請使用 Secret Manager、
Kubernetes Secret、Vault 或雲端 Key Vault，不要把 API Key commit 到 Git。

The gateway is configured through environment variables. In production, store credentials in a
secret-management system rather than committing them to Git.

## Gateway

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_API_KEY` | `dev-gateway-key` | Client key required in `X-API-Key` |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Upstream HTTP timeout |
| `MODEL_ALIASES_JSON` | `{"default":"mock:demo"}` | Alias to `provider:model` |
| `FALLBACK_MODELS_JSON` | `[]` | Ordered fallback candidates |

## Providers

| Provider | Credential | Base URL variable |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` |
| Google Gemini | `GOOGLE_API_KEY` | `GOOGLE_BASE_URL` |
| Mock | none | none |

## Alias example

```dotenv
MODEL_ALIASES_JSON={"fast":"openai:gpt-5-mini","quality":"anthropic:claude-sonnet-4-5"}
```

A client can then send `"model": "fast"` instead of binding itself to a provider.

## Fallback example

```dotenv
FALLBACK_MODELS_JSON=["anthropic:claude-sonnet-4-5","google:gemini-2.5-pro"]
```

The gateway tries the requested target first. Provider configuration or upstream request failures
advance to the next configured candidate. Programming errors are intentionally not swallowed.

## Security note

The built-in API-key check is deliberately small and suitable for a reference implementation.
Enterprise deployments should terminate TLS at an ingress/API management layer and integrate
OIDC/JWT, workload identity, rate limits, audit logs, and secret rotation.
