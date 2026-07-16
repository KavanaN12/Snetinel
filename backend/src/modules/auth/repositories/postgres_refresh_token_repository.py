"""
PostgreSQL implementation of RefreshTokenRepository (Phase 2 — see ADR-002).

Stores only the HASH of the refresh token, mirroring the password-hashing
principle: if this table leaks, the tokens inside it are useless without
also breaking the hash.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.domain.entities import RefreshToken
from src.modules.auth.infrastructure.models import RefreshTokenModel


def _to_entity(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
    )


class PostgresRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        model = RefreshTokenModel(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def revoke(self, token_id: UUID) -> None:
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(revoked_at=datetime.utcnow())
        )
        await self._session.execute(stmt)
        await self._session.flush()
