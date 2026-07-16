"""
Auth service — orchestrates registration, login, token refresh, and logout.

Framework-free: no FastAPI imports here. Raises domain exceptions only;
translation to HTTP status codes happens exclusively in the controller.
This is what makes every method below unit-testable with fake repositories
and zero running database or web server.
"""
import secrets
from datetime import datetime, timedelta, timezone

from src.modules.auth.domain.entities import User
from src.modules.auth.domain.exceptions import (
    InvalidCredentialsError,
    TokenNotFoundError,
    TokenRevokedError,
    UserAlreadyExistsError,
)
from src.modules.auth.domain.value_objects import TokenPair
from src.modules.auth.repositories.refresh_token_repository import RefreshTokenRepository
from src.modules.auth.repositories.user_repository import UserRepository
from src.shared.config.settings import get_settings
from src.shared.security.jwt_handler import JWTHandler
from src.shared.security.password_hasher import PasswordHasher
from src.shared.security.token_hasher import TokenHasher

settings = get_settings()


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository

    async def register(self, email: str, password: str) -> User:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(f"An account with email '{email}' already exists")

        password_hash = PasswordHasher.hash(password)
        return await self._users.create(email=email, password_hash=password_hash)

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)

        # Deliberately identical error for "no such user" and "wrong password" —
        # distinguishing them is a user-enumeration vulnerability.
        if user is None or not user.is_active or not PasswordHasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        return await self._issue_token_pair(user.id)

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        """
        Validates the presented refresh token and issues a NEW token pair,
        revoking the old refresh token in the same operation (rotation).
        This bounds the blast radius of a leaked refresh token to one use.
        """
        token_hash = self._hash_token(raw_refresh_token)
        stored = await self._refresh_tokens.get_by_token_hash(token_hash)

        if stored is None:
            raise TokenNotFoundError("Refresh token not recognized")
        if stored.is_revoked:
            raise TokenRevokedError("Refresh token has been revoked")
        if stored.is_expired(datetime.now(timezone.utc)):
            raise TokenRevokedError("Refresh token has expired")

        await self._refresh_tokens.revoke(stored.id)
        return await self._issue_token_pair(stored.user_id)

    async def logout(self, raw_refresh_token: str) -> None:
        """Idempotent: revoking an already-revoked or unknown token is not an error."""
        token_hash = self._hash_token(raw_refresh_token)
        stored = await self._refresh_tokens.get_by_token_hash(token_hash)
        if stored is not None and not stored.is_revoked:
            await self._refresh_tokens.revoke(stored.id)

    async def _issue_token_pair(self, user_id) -> TokenPair:
        access_token = JWTHandler.create_access_token(str(user_id))

        raw_refresh_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)

        await self._refresh_tokens.create(user_id=user_id, token_hash=token_hash, expires_at=expires_at)

        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """
        Refresh tokens are hashed before storage/lookup using a DETERMINISTIC
        hash (HMAC-SHA256), not bcrypt. Bcrypt's random salt would make the
        same raw token hash differently on every call, breaking equality-based
        lookup in get_by_token_hash(). See TokenHasher docstring for the full
        rationale. This is a deliberate distinction from password hashing,
        not an inconsistency.
        """
        return TokenHasher.hash(raw_token)
