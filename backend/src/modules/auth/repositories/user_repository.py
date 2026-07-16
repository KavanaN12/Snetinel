"""
Abstract UserRepository contract.

Services depend on this Protocol, never on the concrete Postgres
implementation directly — this is what lets auth_service.py be unit tested
with a fake in-memory repository, with zero database involved.
"""
from typing import Protocol
from uuid import UUID

from src.modules.auth.domain.entities import User


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def create(self, email: str, password_hash: str) -> User: ...
