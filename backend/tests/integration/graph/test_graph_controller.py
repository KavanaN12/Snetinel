from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.modules.discovery.infrastructure.models import CloudDiscoveredResourceModel, DiscoveryRunModel


@pytest.mark.asyncio
async def test_graph_build_and_list_endpoints(client, db_session):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "graph-owner@example.com", "password": "password123"},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "graph-owner@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Graph Workspace", "description": "Graph endpoint test"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    build_response = await client.post(f"/api/v1/graph/workspaces/{workspace_id}/build", headers=headers)
    assert build_response.status_code == 200
    body = build_response.json()
    assert body["node_count"] == 0
    assert body["edge_count"] == 0

    list_response = await client.get(f"/api/v1/graph/workspaces/{workspace_id}", headers=headers)
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["node_count"] == 0
    assert list_body["edge_count"] == 0


@pytest.mark.asyncio
async def test_graph_build_and_list_endpoints_persist_graph(client, db_session):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "graph-persist@example.com", "password": "password123"},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "graph-persist@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Persisted Graph Workspace", "description": "Graph persistence test"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    discovery_run = DiscoveryRunModel(
        id=uuid4(),
        workspace_id=workspace_id,
        status="completed",
        summary="Test discovery",
        resource_count=2,
        discovered_resources=[],
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(discovery_run)
    await db_session.flush()
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=workspace_id,
            discovery_run_id=discovery_run.id,
            resource_type="iam_user",
            resource_id="alice",
            name="alice",
            arn=None,
            details={"user_id": "u1"},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=workspace_id,
            discovery_run_id=discovery_run.id,
            resource_type="iam_policy",
            resource_id="policy-1",
            name="policy-1",
            arn=None,
            details={"policy_id": "p1"},
        )
    )
    await db_session.commit()

    build_response = await client.post(f"/api/v1/graph/workspaces/{workspace_id}/build", headers=headers)
    assert build_response.status_code == 200
    build_body = build_response.json()
    assert build_body["node_count"] == 2
    assert build_body["edge_count"] == 1

    list_response = await client.get(f"/api/v1/graph/workspaces/{workspace_id}", headers=headers)
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["node_count"] == 2
    assert list_body["edge_count"] == 1
    assert sorted((node["node_type"], node["external_id"]) for node in list_body["nodes"]) == [
        ("iam_policy", "policy-1"),
        ("iam_user", "alice"),
    ]
    assert list_body["edges"][0]["edge_type"] == "OWNS"
