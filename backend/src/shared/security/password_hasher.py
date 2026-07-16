"""
Password hashing utility.

Thin wrapper over passlib's bcrypt implementation. Deliberately stateless
and framework-free — no DB, no FastAPI — so it can be unit tested with zero
mocking and reused by any module that ever needs to hash a secret
(currently: auth passwords and refresh tokens).
"""
from passlib.context import CryptContext

from src.shared.config.settings import get_settings

_settings = get_settings()

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=_settings.BCRYPT_ROUNDS,
)


class PasswordHasher:
    """Hashes and verifies secrets using bcrypt with a constant-time comparison."""

    @staticmethod
    def hash(plain_text: str) -> str:
        return _pwd_context.hash(plain_text)

    @staticmethod
    def verify(plain_text: str, hashed: str) -> bool:
        """
        Returns False on any mismatch, including malformed hashes — never
        raises, so callers can't accidentally leak timing/error information
        about *why* verification failed.
        """
        try:
            return _pwd_context.verify(plain_text, hashed)
        except (ValueError, TypeError):
            return False
