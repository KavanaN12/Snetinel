# ADR-002: Refresh Token Storage — PostgreSQL in Phase 2, Migrating to Redis in Phase 4

## Status
Accepted

## Context
SAD §6 (Redis Usage) lists refresh token storage as a Redis responsibility
(`refresh:{token}` → `user_id`, TTL 7 days). However, SAD §6 itself, and the
Phase roadmap in SAD §13, place Redis's introduction at **Phase 4** (Cloud
Discovery), justified specifically by discovery's long-running, I/O-bound
workload needing an async job queue. Auth is built in **Phase 2**, before
that justification exists.

Introducing Redis in Phase 2 solely to store refresh tokens would mean
adding a datastore to the system before the SAD's own reasoning for
introducing it applies — the same "complexity before it's earned" problem
already avoided once when the Redis-timing was reconsidered during
architecture review.

## Decision
Refresh tokens are stored in PostgreSQL for Phase 2, in a new
`refresh_tokens` table (see migration `0002_create_refresh_tokens_table.py`
and `RefreshTokenModel`). Only the token's HMAC-SHA256 hash is stored, never
the raw token — mirroring the password-hashing principle.

The `RefreshTokenRepository` Protocol (in
`modules/auth/repositories/refresh_token_repository.py`) is written as a
storage-agnostic interface from the start. `AuthService` depends only on
this Protocol, never on `PostgresRefreshTokenRepository` directly.

## Consequences

**Positive:**
- Phase 2 has zero new infrastructure dependency beyond the Postgres
  instance already required for `users`.
- The migration path to Redis in Phase 4 requires writing a
  `RedisRefreshTokenRepository` implementing the same Protocol and changing
  the DI wiring in `auth_controller.get_auth_service()` — `AuthService`,
  `auth_controller`'s business logic, and every test against `AuthService`
  remain unchanged.

**Negative / accepted tradeoffs:**
- Refresh token lookups incur a relational query instead of an O(1) Redis
  key lookup — acceptable at MVP scale (single-user-session lookups on
  login/refresh/logout, not a hot path).
- TTL-based expiry is enforced in application code
  (`RefreshToken.is_expired()`) rather than natively by the store (Redis TTL
  would expire keys automatically). Expired-but-not-revoked rows will
  accumulate in `refresh_tokens` until a cleanup job removes them — flagged
  here as a known gap, not deferred silently. A scheduled cleanup task is
  planned as part of the Phase 4 Redis migration, not before.

## Migration Plan (Phase 4)
1. Implement `RedisRefreshTokenRepository` satisfying `RefreshTokenRepository`.
2. Swap the concrete class in `auth_controller.get_auth_service()`.
3. Write a one-time data migration copying any still-valid, unexpired
   tokens from `refresh_tokens` into Redis with the correct remaining TTL.
4. Drop the `refresh_tokens` table via a new Alembic migration once cutover
   is verified.
