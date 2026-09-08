# 設定說明 / Configuration

本專案以環境變數設定 Gateway、LLM Provider、路由策略與治理規則。正式環境請使用
Secret Manager、Kubernetes Secret、Vault 或雲端 Key Vault 保存敏感資訊。

The gateway uses environment variables for providers, routing, and governance. Store production
credentials in a secret-management system rather than Git.

## Gateway

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_API_KEY` | `dev-gateway-key` | Client key required in `X-API-Key` |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Upstream HTTP timeout |
| `MODEL_ALIASES_JSON` | `{"default":"mock:demo"}` | Stable alias -> one `provider:model` |
| `MODEL_POOLS_JSON` | `{}` | Logical pool -> candidate model array |
| `FALLBACK_MODELS_JSON` | `[]` | Global fallback candidates |
| `ROUTING_POLICY` | `priority` | Default routing policy |
| `MODEL_PRICING_JSON` | mock price = 0 | Token pricing per 1M tokens |

## Governance

| Variable | Default | Description |
|---|---:|---|
| `PROVIDER_RETRY_ATTEMPTS` | 1 | Retry count for each provider/model candidate |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | 60 | Sliding-window request limit per API key |
| `DAILY_BUDGET_USD` | disabled | Daily accumulated-cost hard limit |
| `MONTHLY_BUDGET_USD` | disabled | Monthly accumulated-cost hard limit |
| `CIRCUIT_FAILURE_THRESHOLD` | 3 | Consecutive provider failures before opening circuit |
| `CIRCUIT_RECOVERY_SECONDS` | 30 | Open-circuit recovery interval |

## Providers

| Provider | Credential | Base URL variable |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` |
| Google Gemini | `GOOGLE_API_KEY` | `GOOGLE_BASE_URL` |
| Mock | none | none |

## Routing policies

### priority

依 `MODEL_POOLS_JSON` 中的順序逐一嘗試。適合主模型 + 備援模型。

### round_robin

每次 request 旋轉候選模型順序，適合在多個等價 deployment 間分流。

### random

每次 request 隨機排列候選模型。

### cost

依 `MODEL_PRICING_JSON` 的 input + output 單價由低到高排序。沒有價格資料的模型會排在
已知價格模型之後。

Request 可覆寫預設策略：

```json
{
  "model": "balanced",
  "routing_policy": "cost",
  "messages": [{"role": "user", "content": "Hello"}]
}
```

## Model pool example

```dotenv
MODEL_POOLS_JSON={"balanced":["openai:gpt-5-mini","anthropic:claude-sonnet-4-5"],"cheap":["google:gemini-2.5-flash","openai:gpt-5-mini"]}
```

## Pricing example

價格由管理者維護，單位為 USD / 1M tokens：

```dotenv
MODEL_PRICING_JSON={"openai:gpt-5-mini":{"input_per_million":1.0,"output_per_million":4.0},"mock:demo":{"input_per_million":0,"output_per_million":0}}
```

Gateway 使用 Provider 回傳的 token usage 計算實際成本。若沒有該模型價格，仍允許請求，
但 `pricing_known=false` 且該次成本記為 0。

## Budget behavior

Budget 在每次 Chat Completion 前檢查「已累積實際成本」。當日或當月成本已達限制時，
Gateway 回傳 HTTP 429。v0.2 不會預估本次尚未發生的 token cost。

## Runtime state limitation

v0.2 的 usage、budget counter、rate limit 與 circuit breaker 都存於單一 process memory。
重啟服務後會重置，多 replica 之間也不共享。這是刻意的 reference implementation；
v0.3 將改為 Redis-backed distributed state。

## Security note

內建 API key 是示範層級。企業部署仍應在 Ingress / API Management 整合 TLS、OIDC/JWT、
workload identity、secret rotation、audit log 與 WAF / network policy。
