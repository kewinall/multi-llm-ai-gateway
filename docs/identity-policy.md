# Enterprise Identity & Policy / 企業身份與政策

## Authentication modes

v0.5 supports both existing API keys and optional OIDC JWT bearer identity.

### API key

```http
X-API-Key: llmgw_<managed-key>
```

### OIDC bearer

```http
Authorization: Bearer <jwt>
```

OIDC is enabled only when all three values are configured:

```dotenv
OIDC_ISSUER=https://id.example.com/
OIDC_AUDIENCE=ai-gateway
OIDC_JWKS_URL=https://id.example.com/.well-known/jwks.json
```

JWT validation checks:

- signature against JWKS
- configured issuer
- configured audience
- `exp`
- `iat`
- `sub`

Default allowed signing algorithm is `RS256`.

## Claims -> Gateway Principal

Config:

```dotenv
OIDC_ROLE_CLAIM=roles
OIDC_NAME_CLAIM=preferred_username
OIDC_DEFAULT_ROLE=viewer
```

Gateway roles remain:

- viewer
- operator
- admin

When a roles claim contains several Gateway roles, the strongest role wins:
`admin > operator > viewer`.

## Policy Engine

Runtime policies are stored in the Governance Store and, with Redis, are shared by every replica.

Policy fields:

| Field | Meaning |
|---|---|
| `enabled` | enable/disable rule |
| `priority` | lower number evaluated first |
| `effect` | allow / deny |
| `roles` | optional role match |
| `clients` | optional principal ID match |
| `models` | optional glob match such as `openai:*` |
| `allow_stream` | optionally allow/deny streaming |
| `max_tokens` | maximum requested output tokens |

Rules use first-match evaluation by priority. If no rule denies or explicitly matches, the default
is allow for backward compatibility.

Example:

```bash
curl -X PUT http://localhost:8000/admin/api/policies/deny-secret \
  -H 'X-Admin-Key: dev-admin-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "priority": 1,
    "effect": "deny",
    "models": ["openai:secret-*"]
  }'
```

## API key rotation

Managed client keys can be rotated without changing the client identity:

```http
POST /admin/api/clients/{client_id}/rotate-key
```

The new plaintext key is returned once. The old digest is deleted immediately, so the previous key
stops authenticating as soon as rotation succeeds. Rotation is recorded in the audit log.
