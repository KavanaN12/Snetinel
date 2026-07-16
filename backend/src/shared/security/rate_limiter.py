"""
Rate limiter for sensitive endpoints (currently: /auth/login).

SAD amendment (see docs/architecture/ADR-003): login rate limiting was added
to the MVP alongside the existing discovery-trigger rate limit, since login
is a classic brute-force target.

Phase-2 implementation is in-memory (single-process), consistent with the
Redis deferral to Phase 4 (ADR-002). The interface below is intentionally
storage-agnostic (`RateLimiter` protocol) so the Phase 4 migration only
requires a new implementation of `check_and_increment`, not a rewrite of
call sites.

Known Phase-2 limitation, documented not hidden: in-memory state does not
survive process restarts and does not coordinate across multiple worker
processes. Acceptable for MVP single-instance deployment; called out
explicitly as a scaling gap resolved by the Phase 4 Redis migration.
"""
import time
from collections import defaultdict
from typing import Protocol

from src.shared.config.settings import get_settings

settings = get_settings()


class RateLimiter(Protocol):
    def check_and_increment(self, key: str) -> bool:
        """Returns True if the request is allowed, False if rate-limited."""
        ...


class InMemoryRateLimiter:
    """
    Fixed-window counter keyed by an arbitrary string (e.g. `login:{email}`).
    Not thread-safe across multiple processes — see module docstring.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check_and_increment(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self._window_seconds

        # Drop hits outside the current window
        self._hits[key] = [t for t in self._hits[key] if t > window_start]

        if len(self._hits[key]) >= self._max_attempts:
            return False

        self._hits[key].append(now)
        return True


_login_rate_limiter = InMemoryRateLimiter(
    max_attempts=settings.LOGIN_RATE_LIMIT_ATTEMPTS,
    window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
)


def get_login_rate_limiter() -> InMemoryRateLimiter:
    """FastAPI dependency accessor — returns the process-wide limiter instance."""
    return _login_rate_limiter
