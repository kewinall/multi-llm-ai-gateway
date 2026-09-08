# Admin Console / 管理主控台

v0.4 提供內建管理頁面：

```text
GET /admin
```

預設以 `ADMIN_API_KEY` 搭配 `X-Admin-Key` 驗證管理 API。

## 可管理項目

- Runtime / distributed governance 狀態
- Routing Policy
- Model Alias
- Model Pool
- Pricing
- API Client
- RBAC role
- Per-client RPM override
- Audit Log

## RBAC

| Role | Read APIs | Chat Completion | Admin APIs |
|---|---|---|---|
| viewer | Yes | No | No |
| operator | Yes | Yes | No |
| admin | Yes | Yes | Yes |

既有 `GATEWAY_API_KEY` 保持相容並視為 bootstrap operator。
`ADMIN_API_KEY` 視為 bootstrap admin。

Managed client key 只在建立時回傳一次；Gateway 僅保存 SHA-256 hash。

## Dynamic governance

Admin 對 alias、pool、pricing、routing policy 的修改會寫入 governance store。
當 backend 是 Redis 時，多個 Gateway replicas 立即共享設定，不需重新啟動。
