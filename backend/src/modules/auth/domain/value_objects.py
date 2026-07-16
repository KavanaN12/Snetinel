"""
Auth value objects — immutable, no identity of their own.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPair:
    """
    Returned by the auth service on login/refresh. `refresh_token` here is
    the RAW opaque token, given to the client exactly once — only its hash
    is ever persisted (see PostgresRefreshTokenRepository).
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
