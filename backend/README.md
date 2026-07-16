# Sentinel Backend — Phase 2 (Authentication)

Implements the Auth module per the approved Software Architecture Document
(`docs/architecture/` at repo root) and the Phase 2 design discussion:
register, login, refresh (with rotation), logout, and the shared
`get_current_user_id` dependency other modules will consume starting
Phase 3 (Workspace Management).

## What's implemented

- Clean Architecture layering: `controllers -> services -> domain <- repositories <- infrastructure`
- JWT access tokens (HS256, 15 min TTL, `sub`/`iat`/`exp` only)
- Refresh tokens: opaque, HMAC-SHA256-hashed, rotated on every refresh,
  stored in PostgreSQL for Phase 2 (see `docs/architecture/ADR-002-*.md`)
- bcrypt password hashing (cost factor 12, configurable)
- Login rate limiting, in-memory for Phase 2 (see `docs/architecture/ADR-003-*.md`)
- User-enumeration-safe error handling (login failure is indistinguishable
  between "wrong password" and "no such user")
- Full unit test suite (zero database required) + integration test suite
  (requires a running Postgres)

## Project layout

```
backend/
├── src/
│   ├── main.py                     # FastAPI composition root
│   ├── shared/
│   │   ├── config/settings.py      # env-driven settings
│   │   ├── security/                # password/JWT/token hashing, rate limiter,
│   │   │                            # and get_current_user_id (consumed by all modules)
│   │   ├── db/session.py           # async engine/session, declarative Base
│   │   └── domain/exceptions.py    # base exception hierarchy
│   └── modules/auth/
│       ├── controllers/            # FastAPI router, HTTP <-> domain translation
│       ├── services/               # AuthService — framework-free business logic
│       ├── domain/                 # entities, value objects, exceptions
│       ├── repositories/           # Protocols + Postgres implementations
│       └── infrastructure/         # SQLAlchemy ORM models
├── migrations/                     # Alembic, 0001 (users), 0002 (refresh_tokens)
├── tests/
│   ├── unit/auth/                  # no DB, no FastAPI — pure logic
│   └── integration/auth/           # full HTTP stack against real Postgres
├── requirements.txt
├── alembic.ini
├── Dockerfile
└── .env.example
```

## Running locally (Docker)

```bash
cd infrastructure
docker compose up
```

This runs Alembic migrations automatically before starting the API.
API available at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`.

## Running locally (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit JWT_SECRET_KEY and DATABASE_URL as needed
alembic upgrade head
uvicorn src.main:app --reload
```

## Running tests

**Unit tests** — no infrastructure required, run anywhere:

```bash
pytest tests/unit -v
```

**Integration tests** — require a running test Postgres database:

```bash
docker run -d --name sentinel-test-pg -p 5432:5432 \
  -e POSTGRES_USER=sentinel -e POSTGRES_PASSWORD=sentinel -e POSTGRES_DB=sentinel_test \
  postgres:16

TEST_DATABASE_URL=postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_test \
  pytest tests/integration -v
```

**Note on this delivery:** all 52 Python files were statically validated
(`python -m py_compile`) with zero syntax/import errors. The unit and
integration suites themselves could not be executed in the environment
this code was written in (no network access to install dependencies) — run
them per the commands above before treating this phase as verified. This
is stated explicitly rather than implying a test run happened that didn't.

## API Endpoints (Phase 2)

| Method | Path | Auth required |
|---|---|---|
| POST | `/api/v1/auth/register` | No |
| POST | `/api/v1/auth/login` | No (rate-limited) |
| POST | `/api/v1/auth/refresh` | No (refresh token itself is the credential) |
| POST | `/api/v1/auth/logout` | No (refresh token itself is the credential) |
| GET | `/health` | No |

## Deliberate scope cuts (documented, not oversights)

- No password reset flow — out of MVP per Phase 2 design discussion.
- No email verification on registration — same.
- Refresh tokens in Postgres, not Redis — see ADR-002; migrates in Phase 4.
- Rate limiting is in-memory, single-process — see ADR-003; migrates in Phase 4.

## Alignment with the SAD

- **§4 (PostgreSQL Schema):** `users` table matches exactly. `refresh_tokens`
  table is an approved, documented addition (ADR-002), not present in the
  original SAD table list.
- **§7 (API Specification):** all four auth endpoints match the SAD; login
  rate limiting is an approved amendment (ADR-003).
- **§11 (Security Model):** HS256 JWT (documented tradeoff), workspace
  isolation groundwork laid via `get_current_user_id` returning only a
  verified `user_id` — no workspace trust embedded in the token, consistent
  with "never trust client-supplied scoping."
- **§12 (Design Patterns):** Repository pattern (Protocols +
  Postgres impls), DTOs at controller boundaries (request/response
  schemas), DI via FastAPI `Depends()` throughout.
