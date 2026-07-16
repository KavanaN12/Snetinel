# ADR-003: Login Rate Limiting (SAD Amendment)

## Status
Accepted — amends SAD §7 (API Specification)

## Context
SAD §7 and §11 specify rate limiting only for the discovery-trigger
endpoint (`POST /workspaces/{id}/discovery/run`), justified there as
"cheap to abuse, expensive to run." During Phase 2 detailed design, this was
identified as an incomplete threat model: `/auth/login` is a classic
brute-force target and was not covered by any rate limit in the original
SAD.

## Decision
Add rate limiting to `POST /api/v1/auth/login`. Phase 2 implementation uses
an in-memory fixed-window counter (`InMemoryRateLimiter` in
`shared/security/rate_limiter.py`), keyed by `email + client IP`, default
5 attempts per 5-minute window (configurable via `LOGIN_RATE_LIMIT_ATTEMPTS`
/ `LOGIN_RATE_LIMIT_WINDOW_SECONDS`).

The `RateLimiter` Protocol is written storage-agnostic, consistent with the
pattern established in ADR-002 for refresh tokens — a future
`RedisRateLimiter` (Phase 4) can replace `InMemoryRateLimiter` without
touching `auth_controller.py`.

## Consequences

**Positive:**
- Closes a real gap in the original SAD's threat model before any code
  shipped, rather than discovering it in a later security review.
- Keying by `email + IP` (not just IP) limits both a single attacker
  hammering one account and a distributed spray against many accounts from
  one source, without needing a global lock.

**Negative / accepted tradeoffs:**
- In-memory state is per-process: does not coordinate across multiple
  backend worker processes/instances, and resets on restart. This is
  explicitly acceptable for a single-instance MVP deployment and is
  resolved by the Phase 4 Redis migration (shared counter across
  processes), consistent with the Redis-introduction timing already
  established in the SAD.
- Rate limiting by email allows an attacker to intentionally lock out a
  legitimate user by deliberately failing login attempts against their
  address (a denial-of-service on that one account). Accepted for MVP;
  worth revisiting with a CAPTCHA or exponential backoff strategy post-MVP
  if this becomes a real concern.

## SAD Update
SAD §7 and §11 should be read as amended: rate limiting now applies to both
`POST /workspaces/{id}/discovery/run` and `POST /auth/login`.
