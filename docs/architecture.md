# 架構設計 / Architecture

## 目標 / Goal

讓 Agent、RAG、Web 應用與批次工作只整合一種 Chat Completion API，同時把模型選擇、
fallback、成本、預算與 resilience 集中在 Gateway 控制。

## Request flow

```text
Client
  |
  v
API key authentication
  |
  v
Rate limiter ---------> 429 when exceeded
  |
  v
Budget check ---------> 429 when exhausted
  |
  v
Model pool + routing policy
  |   priority / round_robin / random / cost
  v
Circuit breaker
  |
  v
Provider retry
  |
  +------ failure ------> next candidate / fallback
  |
  v
Provider adapter
  |
  v
Normalized OpenAI-style response
  |
  v
Token usage -> pricing -> usage store -> budget counters
  |
  v
Response + routing/cost metadata + X-Request-ID
```

## Components

```text
app/main.py
  |
  +-- security.py
  +-- rate_limit.py
  +-- budget.py
  +-- usage.py
  +-- pricing.py
  +-- resilience.py
  |
  +-- router.py
        |
        +-- providers/openai.py
        +-- providers/anthropic.py
        +-- providers/google.py
        +-- providers/mock.py
```

## Routing layer

### Alias

一個 stable name 對應一個實體模型，例如 `default -> mock:demo`。

### Pool

一個 logical name 對應多個候選模型，例如 `balanced -> [OpenAI, Anthropic, Gemini]`。
Policy 決定候選順序，provider failure 則依序嘗試後續模型。

### Routing metadata

每次成功回應都包含：

- requested model
- selected provider/model
- routing policy
- candidate order
- 每次 provider attempt / retry 結果
- fallback 是否發生
- 本次估算成本與 pricing-known flag
- request 完成後的 budget 狀態

## Governance layer

### Usage & pricing

Gateway 使用 normalized `usage.prompt_tokens` / `completion_tokens` 計算成本，並依
provider:model 累積 token 與 USD 使用量。

### Rate limit

v0.2 採 per-API-key 60-second sliding window。

### Budget

支援 daily / monthly USD hard limit，檢查的是已累積實際成本。

### Circuit breaker

Provider 達到 failure threshold 後進入 open state；recovery window 後允許 probe，
成功後回 closed。

## API surface

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat request |
| `GET /v1/providers` | Provider configuration + circuit state |
| `GET /v1/models` | Alias, pools, pricing and default policy |
| `GET /v1/usage` | Token / request / cost accounting |
| `GET /v1/budgets` | Daily and monthly budget status |
| `GET /health` | Service health |

## v0.2 limitation / v0.3 boundary

所有 runtime governance state 都是 process-local memory，因此 v0.2 適合單 instance、
PoC、架構展示與 integration testing。v0.3 會將這些 state 移到 Redis，並加入 metrics、
tracing 與分散式觀測能力。
