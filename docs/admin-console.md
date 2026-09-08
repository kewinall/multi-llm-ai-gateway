# Admin Console / 管理主控台

v0.5 Admin Console:

```text
GET /admin
```

Bootstrap administration uses:

```text
X-Admin-Key: ADMIN_API_KEY
```

Managed `admin` client keys may also call Admin API using `X-API-Key`.

## Console capabilities

- Runtime / distributed governance status
- Routing Policy
- Model Alias
- Model Pool
- Pricing
- Request Policies
- API Clients
- RBAC role
- Per-client RPM override
- API key rotation
- Audit Log

## Request Policy form

The console can configure:

- effect: allow / deny
- roles
- model glob patterns
- stream allow/deny
- max tokens

Advanced policy fields such as explicit client principal IDs remain available through Admin API.

## Key rotation

The Client table includes a **Rotate** action.

Rotation:

1. generates a new `llmgw_` key
2. stores only its SHA-256 digest
3. removes the previous digest
4. returns plaintext once
5. records an audit event

## RBAC

| Role | Read APIs | Chat Completion | Admin APIs |
|---|---:|---:|---:|
| viewer | Yes | No | No |
| operator | Yes | Yes | No |
| admin | Yes | Yes | Yes |

OIDC identities map into the same role model.

## Distributed behavior

With Redis active, aliases, pools, pricing, routing policy, request policies, client-key state, and
audit events are shared by all Gateway replicas without restart.
