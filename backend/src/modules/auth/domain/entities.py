"""
Auth domain entities.

Pure Python dataclasses — no SQLAlchemy, no Pydantic. These represent the
concept of a User/RefreshToken independent of how they're persisted or
transported over HTTP. The infrastructure layer maps ORM rows to these;
the schemas layer maps these to API responses. Neither mapping happens here.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
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
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now >= expires_at
