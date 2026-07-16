"""
Deterministic hashing for opaque tokens (refresh tokens).

This is intentionally NOT bcrypt. Bcrypt salts every hash randomly, which is
correct for passwords (verified via a compare function) but WRONG for
refresh tokens, which must be looked up by exact hash equality
(`WHERE token_hash = ?`) — a random salt would make the same raw token
hash differently every time and the lookup would never match.

HMAC-SHA256 keyed with the JWT secret gives us: deterministic output (safe
for equality lookups), resistance to length-extension attacks (unlike plain
SHA-256), and a hash that's useless to an attacker without also knowing the
server-side key, even if the refresh_tokens table leaks on its own.
"""
import hashlib
import hmac

from src.shared.config.settings import get_settings

settings = get_settings()


class TokenHasher:
    @staticmethod
    def hash(raw_token: str) -> str:
        return hmac.new(
            key=settings.JWT_SECRET_KEY.encode("utf-8"),
            msg=raw_token.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
