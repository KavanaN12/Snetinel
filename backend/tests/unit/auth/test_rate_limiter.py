from src.shared.security.rate_limiter import InMemoryRateLimiter


class TestInMemoryRateLimiter:
    def test_allows_requests_under_the_limit(self):
        limiter = InMemoryRateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.check_and_increment("key-a") is True
        assert limiter.check_and_increment("key-a") is True
        assert limiter.check_and_increment("key-a") is True

    def test_blocks_requests_over_the_limit(self):
        limiter = InMemoryRateLimiter(max_attempts=2, window_seconds=60)
        assert limiter.check_and_increment("key-b") is True
        assert limiter.check_and_increment("key-b") is True
        assert limiter.check_and_increment("key-b") is False

    def test_keys_are_independent(self):
        limiter = InMemoryRateLimiter(max_attempts=1, window_seconds=60)
        assert limiter.check_and_increment("user-1") is True
        assert limiter.check_and_increment("user-2") is True
        assert limiter.check_and_increment("user-1") is False

    def test_window_expiry_allows_requests_again(self):
        """Uses a zero-second window so old hits are immediately stale."""
        limiter = InMemoryRateLimiter(max_attempts=1, window_seconds=0)
        assert limiter.check_and_increment("key-c") is True
        assert limiter.check_and_increment("key-c") is True  # prior hit already outside 0s window
