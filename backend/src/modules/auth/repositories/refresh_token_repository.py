"""
Abstract RefreshTokenRepository contract.

Phase 2: backed by PostgreSQL (see ADR-002). Phase 4: a RedisRefreshTokenRepository
implementing this same Protocol will replace it at the DI wiring point in
main.py — auth_service.py will not change.
"""
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.auth.domain.entities import RefreshToken


class RefreshTokenRepository(Protocol):
    async def create(self, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken: ...

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def revoke(self, token_id: UUID) -> None: ...
