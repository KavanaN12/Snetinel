from src.shared.security.token_hasher import TokenHasher


class TestTokenHasher:
    def test_hash_is_deterministic(self):
        """
        Unlike PasswordHasher (bcrypt, salted), TokenHasher MUST be
        deterministic — refresh tokens are looked up by exact hash equality.
        """
        token = "some-opaque-refresh-token-value"
        assert TokenHasher.hash(token) == TokenHasher.hash(token)

    def test_different_tokens_produce_different_hashes(self):
        assert TokenHasher.hash("token-a") != TokenHasher.hash("token-b")

    def test_hash_output_is_hex_sha256_length(self):
        result = TokenHasher.hash("any-token")
        assert len(result) == 64  # SHA-256 hex digest length
        int(result, 16)  # raises ValueError if not valid hex
