import pytest

from src.modules.auth.domain.exceptions import (
    InvalidCredentialsError,
    TokenNotFoundError,
    TokenRevokedError,
    UserAlreadyExistsError,
)
from src.modules.auth.services.auth_service import AuthService
from tests.unit.auth.fakes import FakeRefreshTokenRepository, FakeUserRepository


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService(
        user_repository=FakeUserRepository(),
        refresh_token_repository=FakeRefreshTokenRepository(),
    )


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_creates_user_with_hashed_password(self, auth_service):
        user = await auth_service.register(email="alice@example.com", password="s3cur3-password")
        assert user.email == "alice@example.com"
        assert user.password_hash != "s3cur3-password"

    @pytest.mark.asyncio
    async def test_register_rejects_duplicate_email(self, auth_service):
        await auth_service.register(email="bob@example.com", password="password123")
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register(email="bob@example.com", password="different-password")


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_succeeds_with_correct_credentials(self, auth_service):
        await auth_service.register(email="carol@example.com", password="correct-password")
        token_pair = await auth_service.login(email="carol@example.com", password="correct-password")
        assert token_pair.access_token
        assert token_pair.refresh_token
        assert token_pair.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_fails_with_wrong_password(self, auth_service):
        await auth_service.register(email="dave@example.com", password="correct-password")
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(email="dave@example.com", password="wrong-password")

    @pytest.mark.asyncio
    async def test_login_fails_for_nonexistent_user(self, auth_service):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(email="ghost@example.com", password="anything")

    @pytest.mark.asyncio
    async def test_login_error_message_does_not_distinguish_user_existence(self, auth_service):
        """Enumeration-safety: both failure modes must raise the identical message."""
        await auth_service.register(email="erin@example.com", password="correct-password")

        with pytest.raises(InvalidCredentialsError) as wrong_pw_exc:
            await auth_service.login(email="erin@example.com", password="wrong-password")

        with pytest.raises(InvalidCredentialsError) as no_user_exc:
            await auth_service.login(email="nobody@example.com", password="wrong-password")

        assert str(wrong_pw_exc.value) == str(no_user_exc.value)


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_issues_new_token_pair(self, auth_service):
        await auth_service.register(email="frank@example.com", password="password123")
        initial = await auth_service.login(email="frank@example.com", password="password123")

        refreshed = await auth_service.refresh(initial.refresh_token)

        assert refreshed.access_token != initial.access_token
        assert refreshed.refresh_token != initial.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_rotates_and_revokes_old_token(self, auth_service):
        """Old refresh token must be unusable after a single refresh (rotation)."""
        await auth_service.register(email="grace@example.com", password="password123")
        initial = await auth_service.login(email="grace@example.com", password="password123")

        await auth_service.refresh(initial.refresh_token)

        with pytest.raises(TokenRevokedError):
            await auth_service.refresh(initial.refresh_token)

    @pytest.mark.asyncio
    async def test_refresh_fails_for_unknown_token(self, auth_service):
        with pytest.raises(TokenNotFoundError):
            await auth_service.refresh("a-token-that-was-never-issued")


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(self, auth_service):
        await auth_service.register(email="henry@example.com", password="password123")
        tokens = await auth_service.login(email="henry@example.com", password="password123")

        await auth_service.logout(tokens.refresh_token)

        with pytest.raises(TokenRevokedError):
            await auth_service.refresh(tokens.refresh_token)

    @pytest.mark.asyncio
    async def test_logout_is_idempotent_for_unknown_token(self, auth_service):
        """Logging out with a bogus/already-revoked token must not raise."""
        await auth_service.logout("never-issued-token")  # should not raise
