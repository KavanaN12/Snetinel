"""
Auth domain entities.

Pure Python dataclasses — no SQLAlchemy, no Pydantic. These represent the
concept of a User/RefreshToken independent of how they're persisted or
transported over HTTP. The infrastructure layer maps ORM rows to these;
the schemas layer maps these to API responses. Neither mapping happens here.
"""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class RefreshToken:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
