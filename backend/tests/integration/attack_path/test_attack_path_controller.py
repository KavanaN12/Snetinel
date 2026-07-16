from datetime import datetime, timezone

import pytest

from src.modules.discovery.infrastructure.models import CloudDiscoveredResourceModel, DiscoveryRunModel


@pytest.mark.asyncio
async def test_attack_path_analyze_and_list_endpoints(client, db_session):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "attack-path@example.com", "password": "password123"},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "attack-path@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Attack Path Workspace", "description": "Attack path test"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    discovery_run = DiscoveryRunModel(
        workspace_id=workspace_id,
        status="completed",
        summary="Attack path discovery",
        resource_count=5,
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
            resource_type="iam_role",
            resource_id="role-1",
            name="role-1",
            arn=None,
            details={"role_id": "r1"},
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
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=workspace_id,
            discovery_run_id=discovery_run.id,
            resource_type="vpc",
            resource_id="vpc-1",
            name="vpc-1",
            arn=None,
            details={"cidr_block": "10.0.0.0/16"},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=workspace_id,
            discovery_run_id=discovery_run.id,
            resource_type="security_group",
            resource_id="sg-1",
            name="sg-1",
            arn=None,
            details={"group_id": "sg1"},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=workspace_id,
            discovery_run_id=discovery_run.id,
            resource_type="ec2_instance",
            resource_id="instance-1",
            name="instance-1",
            arn=None,
            details={"instance_id": "i1"},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=workspace_id,
            discovery_run_id=discovery_run.id,
            resource_type="s3_bucket",
            resource_id="bucket-1",
            name="bucket-1",
            arn=None,
            details={"bucket_name": "bucket"},
        )
    )
    await db_session.commit()

    build_response = await client.post(f"/api/v1/graph/workspaces/{workspace_id}/build", headers=headers)
    assert build_response.status_code == 200

    analyze_response = await client.post(f"/api/v1/attack-path/workspaces/{workspace_id}/analyze", headers=headers)
    assert analyze_response.status_code == 200
    analyze_body = analyze_response.json()
    assert analyze_body["path_count"] >= 4

    list_response = await client.get(f"/api/v1/attack-path/workspaces/{workspace_id}", headers=headers)
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["path_count"] >= 4
