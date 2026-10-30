from uuid import UUID

import pytest


@pytest.mark.asyncio
async def test_scenario_catalog_and_history_are_authenticated_and_workspace_scoped(client):
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "scenario-library@example.com", "password": "password123"},
    )
    assert registration.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "scenario-library@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    unauthenticated = await client.get("/api/v1/scenarios/catalog")
    assert unauthenticated.status_code == 401

    catalog = await client.get("/api/v1/scenarios/catalog", headers=headers)
    assert catalog.status_code == 200
    scenarios = catalog.json()
    assert len(scenarios) == 9
    assert {scenario["difficulty"] for scenario in scenarios} == {
        "easy",
        "intermediate",
        "advanced",
    }
    assert all(scenario["expected_resources"] for scenario in scenarios)

    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Scenario workspace", "description": "isolated scenario API test"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = UUID(workspace_response.json()["id"])

    runs = await client.get(
        f"/api/v1/scenarios/workspaces/{workspace_id}/runs",
        headers=headers,
    )
    assert runs.status_code == 200
    assert runs.json() == []

    unsupported = await client.post(
        f"/api/v1/scenarios/workspaces/{workspace_id}/runs",
        json={"scenario_id": "cross-account-admin"},
        headers=headers,
    )
    assert unsupported.status_code == 422
