"""
PostgreSQL implementation of UserRepository, via SQLAlchemy async session.

Responsible ONLY for translating between UserModel (ORM) and User (domain
entity). No business logic lives here — validation, password hashing, and
error semantics are the service layer's job.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.domain.entities import User
from src.modules.auth.infrastructure.models import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        is_active=model.is_active,
        created_at=model.created_at,
    )


class PostgresUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    async def create(self, email: str, password_hash: str) -> User:
        model = UserModel(email=email, password_hash=password_hash)
        self._session.add(model)
        await self._session.flush()  # populate defaults (id, created_at) without committing
        await self._session.refresh(model)
        return _to_entity(model)
