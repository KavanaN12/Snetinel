import pytest


@pytest.mark.asyncio
async def test_discovery_endpoint_creates_run_for_workspace_owner(client):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "discovery-owner@example.com", "password": "password123"},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "discovery-owner@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Discovery Workspace", "description": "Created for discovery tests"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    discovery_response = await client.post(
        f"/api/v1/discovery/workspaces/{workspace_id}/discover",
        json={"source": "integration"},
        headers=headers,
    )
    assert discovery_response.status_code == 201
    body = discovery_response.json()
    assert body["workspace_id"] == workspace_id
    assert body["status"] == "completed"
    assert body["resource_count"] >= 1
    assert body["summary"].startswith("Discovered workspace")
