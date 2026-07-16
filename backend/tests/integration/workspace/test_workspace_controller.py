import pytest


async def _register_and_login(client, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    return response.json()["access_token"]


class TestWorkspaceEndpoints:
    @pytest.mark.asyncio
    async def test_create_workspace_returns_201_and_body(self, client):
        token = await _register_and_login(client, "workspace-owner@example.com")
        response = await client.post(
            "/api/v1/workspaces",
            json={"name": "Alpha", "description": "Primary workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Alpha"
        assert body["description"] == "Primary workspace"
        assert "id" in body

    @pytest.mark.asyncio
    async def test_list_returns_only_owner_workspaces(self, client):
        owner_token = await _register_and_login(client, "workspace-owner-2@example.com")
        other_token = await _register_and_login(client, "workspace-other@example.com")

        await client.post(
            "/api/v1/workspaces",
            json={"name": "Owned", "description": "Mine"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        await client.post(
            "/api/v1/workspaces",
            json={"name": "Other", "description": "Not mine"},
            headers={"Authorization": f"Bearer {other_token}"},
        )

        response = await client.get(
            "/api/v1/workspaces",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "Owned"

    @pytest.mark.asyncio
    async def test_update_and_delete_require_owner_access(self, client):
        owner_token = await _register_and_login(client, "workspace-owner-3@example.com")
        other_token = await _register_and_login(client, "workspace-other-2@example.com")

        create_response = await client.post(
            "/api/v1/workspaces",
            json={"name": "Shared", "description": "Initial"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        workspace_id = create_response.json()["id"]

        update_response = await client.patch(
            f"/api/v1/workspaces/{workspace_id}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert update_response.status_code == 403

        delete_response = await client.delete(
            f"/api/v1/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert delete_response.status_code == 204
