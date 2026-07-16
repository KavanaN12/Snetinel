"""
Fake repositories implementing the same Protocols as the Postgres
implementations. Used exclusively in unit tests, proving AuthService has no
hidden dependency on SQLAlchemy or a running database.
"""
import uuid
from datetime import datetime

from src.modules.auth.domain.entities import RefreshToken, User


class FakeUserRepository:
    def __init__(self) -> None:
        self._users: dict[uuid.UUID, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._users.get(user_id)

    async def create(self, email: str, password_hash: str) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        self._users[user.id] = user
        return user


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[uuid.UUID, RefreshToken] = {}

    async def create(self, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        self._tokens[token.id] = token
        return token

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self._tokens.values() if t.token_hash == token_hash), None)

    async def revoke(self, token_id: uuid.UUID) -> None:
        existing = self._tokens[token_id]
        self._tokens[token_id] = RefreshToken(
            id=existing.id,
            user_id=existing.user_id,
            token_hash=existing.token_hash,
            expires_at=existing.expires_at,
            revoked_at=datetime.utcnow(),
        )
