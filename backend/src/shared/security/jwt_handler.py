"""
JWT access token handling.

Per SAD Phase-2 Auth design: access tokens are short-lived JWTs (HS256)
carrying only `sub` (user_id), `iat`, and `exp` — no email, no roles, no
workspace claims. Workspace membership is always resolved by a fresh DB
lookup per request (SAD §11), never trusted from token contents.

Refresh tokens are NOT JWTs — they are opaque random strings handled in
modules/auth/services/auth_service.py and are out of scope for this file.
"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from src.shared.config.settings import get_settings

settings = get_settings()


class TokenExpiredError(Exception):
    """Raised when a JWT's exp claim has passed."""


class TokenInvalidError(Exception):
    """Raised when a JWT is malformed, has an invalid signature, or fails decode."""


class JWTHandler:
    """Encodes and decodes short-lived access tokens."""

    @staticmethod
    def create_access_token(user_id: str) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES)
        payload = {"sub": user_id, "iat": now, "exp": expire}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> str:
        """
        Decodes a token and returns the user_id (sub claim).
        Raises TokenExpiredError or TokenInvalidError — callers translate
        these to HTTP 401 at the controller/dependency boundary.
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError("Access token has expired") from exc
        except JWTError as exc:
            raise TokenInvalidError("Access token is invalid") from exc

        user_id = payload.get("sub")
        if not user_id:
            raise TokenInvalidError("Access token missing subject claim")
        return user_id
