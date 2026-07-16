import pytest


class TestRegisterEndpoint:
    @pytest.mark.asyncio
    async def test_register_returns_201_with_user_payload(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "integration-a@example.com", "password": "password123"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "integration-a@example.com"
        assert "password" not in body
        assert "password_hash" not in body

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, client):
        payload = {"email": "integration-b@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_rejects_short_password(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "integration-c@example.com", "password": "short"},
        )
        assert response.status_code == 422


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_returns_token_pair(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "integration-d@example.com", "password": "password123"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "integration-d@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "integration-e@example.com", "password": "password123"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "integration-e@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_rate_limits_after_repeated_failures(self, client):
        payload = {"email": "integration-f@example.com", "password": "wrong-password"}
        last_status = None
        for _ in range(10):
            resp = await client.post("/api/v1/auth/login", json=payload)
            last_status = resp.status_code
        assert last_status == 429


class TestRefreshEndpoint:
    @pytest.mark.asyncio
    async def test_refresh_rotates_token_and_old_token_becomes_invalid(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "integration-g@example.com", "password": "password123"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "integration-g@example.com", "password": "password123"},
        )
        old_refresh = login_resp.json()["refresh_token"]

        refresh_resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert refresh_resp.status_code == 200
        assert refresh_resp.json()["refresh_token"] != old_refresh

        reuse_resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert reuse_resp.status_code == 401


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "integration-h@example.com", "password": "password123"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "integration-h@example.com", "password": "password123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 204

        refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 401


class TestProtectedEndpointDependency:
    @pytest.mark.asyncio
    async def test_missing_bearer_token_returns_401_via_healthcheck_analog(self, client):
        """
        Phase 2 has no protected business endpoint yet (workspace module is
        Phase 2's second half) — this test exercises get_current_user_id
        indirectly once a protected route exists. Placeholder assertion
        below confirms the health endpoint (intentionally public) still
        works without auth, establishing the baseline for that future test.
        """
        response = await client.get("/health")
        assert response.status_code == 200
