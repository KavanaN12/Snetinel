from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from src.shared.config.settings import get_settings
from src.shared.security.jwt_handler import JWTHandler, TokenExpiredError, TokenInvalidError

settings = get_settings()


class TestJWTHandler:
    def test_create_and_decode_round_trip(self):
        user_id = "11111111-1111-1111-1111-111111111111"
        token = JWTHandler.create_access_token(user_id)
        decoded_user_id = JWTHandler.decode_access_token(token)
        assert decoded_user_id == user_id

    def test_token_payload_contains_no_extra_claims(self):
        """Per SAD Phase-2 design: token carries only sub/iat/exp — nothing else."""
        user_id = "22222222-2222-2222-2222-222222222222"
        token = JWTHandler.create_access_token(user_id)
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert set(payload.keys()) == {"sub", "iat", "exp"}

    def test_decode_raises_on_expired_token(self):
        user_id = "33333333-3333-3333-3333-333333333333"
        expired_payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc) - timedelta(minutes=30),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=15),
        }
        expired_token = jwt.encode(
            expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        with pytest.raises(TokenExpiredError):
            JWTHandler.decode_access_token(expired_token)

    def test_decode_raises_on_invalid_signature(self):
        token = JWTHandler.create_access_token("some-user-id")
        tampered = token[:-2] + "xx"
        with pytest.raises(TokenInvalidError):
            JWTHandler.decode_access_token(tampered)

    def test_decode_raises_on_garbage_input(self):
        with pytest.raises(TokenInvalidError):
            JWTHandler.decode_access_token("not-a-jwt-at-all")

    def test_decode_raises_on_missing_subject_claim(self):
        payload = {
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(TokenInvalidError):
            JWTHandler.decode_access_token(token)
