from src.shared.security.password_hasher import PasswordHasher


class TestPasswordHasher:
    def test_hash_produces_different_output_than_input(self):
        hashed = PasswordHasher.hash("correct-horse-battery-staple")
        assert hashed != "correct-horse-battery-staple"

    def test_hash_is_salted_and_nondeterministic(self):
        """Same plaintext hashed twice must produce different bcrypt output (random salt)."""
        h1 = PasswordHasher.hash("same-password")
        h2 = PasswordHasher.hash("same-password")
        assert h1 != h2

    def test_verify_succeeds_with_correct_password(self):
        hashed = PasswordHasher.hash("my-secret-pw")
        assert PasswordHasher.verify("my-secret-pw", hashed) is True

    def test_verify_fails_with_incorrect_password(self):
        hashed = PasswordHasher.hash("my-secret-pw")
        assert PasswordHasher.verify("wrong-password", hashed) is False

    def test_verify_returns_false_on_malformed_hash_without_raising(self):
        assert PasswordHasher.verify("anything", "not-a-real-bcrypt-hash") is False

    def test_verify_returns_false_on_empty_hash(self):
        assert PasswordHasher.verify("anything", "") is False
