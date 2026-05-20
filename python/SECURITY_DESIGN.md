# Security Design (Member C)

## Scope

This iteration hardens API baseline security for classroom defense, focusing on:

- Admin API key authentication
- CORS whitelist configuration
- Request input constraints
- Rate limit abuse protection
- Prompt-injection-aware LLM input sanitization

## Threat Model Snapshot

| Asset | Threat | Control |
|---|---|---|
| Experiment and metrics data | Unauthorized read/write of admin endpoints | `X-API-Key` check on `/api/v1/experiments`, `/api/v1/metrics`, `/api/v1/experiments/{id}/outcome` |
| Recommendation API availability | Bot abuse / burst traffic | Per `user_id + IP` in-memory rate limiter with 429 rejection and structured logs |
| Service stability | Oversized or malformed request payload | Pydantic boundary validation for `user_id`, `scene`, `num_items`, `context` size |
| LLM output safety | Prompt injection in product/user fields | Prompt field sanitization and suspicious-token filtering before LLM invocation |
| Browser-side data access | Cross-origin abuse | Configurable CORS allowlist instead of wildcard `*` |

## Security Controls and Configuration

### 1) Admin Endpoint Authentication

- Header: `X-API-Key`
- Config: `ECOM_ADMIN_API_KEY`
- Behavior:
  - Missing/wrong key -> `401`
  - Key not configured -> `503` (fail closed for admin operations)

### 2) CORS Hardening

- Config:
  - `ECOM_CORS_ALLOW_ORIGINS`
  - `ECOM_CORS_ALLOW_METHODS`
  - `ECOM_CORS_ALLOW_HEADERS`
- Default is localhost whitelist for development.

### 3) Input Validation

`RecommendationRequest` constraints:

- `user_id`: non-empty, max 64 chars
- `scene`: non-empty, max 64 chars
- `num_items`: `1..50`
- `context`: max 30 keys, max 4096 chars (stringified)

### 4) Rate Limiting

- Scope: `/api/v1/recommend`, `/api/v1/recommend/graph`
- Key: `user_id + client_ip + path`
- Config:
  - `ECOM_RATE_LIMIT_ENABLED`
  - `ECOM_RATE_LIMIT_WINDOW_SECONDS`
  - `ECOM_RATE_LIMIT_RECOMMEND_PER_WINDOW`
  - `ECOM_RATE_LIMIT_GRAPH_PER_WINDOW`
- On limit hit: `429` + warning log `security.rate_limit_hit.user`

### 5) LLM Prompt Sanitization

Before constructing product prompt lines:

- Truncate long fields
- Filter suspicious patterns (`ignore previous instructions`, role markers, fenced blocks, token wrappers)
- Keep existing ad-law forbidden-word compliance filter

## Demo Script (Attack / Defense)

1. Access `/api/v1/experiments` without `X-API-Key` -> expect `401`.
2. Repeat `/api/v1/recommend` requests for same user beyond limit -> expect `429`.
3. Send over-limit `num_items` or huge `context` -> expect `422`.
4. Show server log entries for rate-limit hits and blocked requests.
