from datetime import datetime, timezone
from uuid import UUID

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
        workspace_id=UUID(workspace_id),
        status="completed",
        summary="Attack path discovery",
        resource_count=5,
        discovered_resources=[],
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(discovery_run)
    await db_session.flush()
    user_arn = "arn:aws:iam::000000000000:user/alice"
    role_arn = "arn:aws:iam::000000000000:role/role-1"
    policy_arn = "arn:aws:iam::000000000000:policy/policy-1"
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sts:AssumeRole",
                    "iam:PassRole",
                    "s3:ListBucket",
                    "ec2:StartInstances",
                    "kms:Decrypt",
                    "lambda:InvokeFunction",
                ],
                "Resource": "*",
            }
        ],
    }
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=UUID(workspace_id),
            discovery_run_id=discovery_run.id,
            resource_type="iam_user",
            resource_id="alice",
            name="alice",
            arn=user_arn,
            details={"user_id": "u1", "arn": user_arn, "attached_policy_arns": [policy_arn]},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=UUID(workspace_id),
            discovery_run_id=discovery_run.id,
            resource_type="iam_role",
            resource_id="role-1",
            name="role-1",
            arn=role_arn,
            details={
                "role_id": "r1",
                "arn": role_arn,
                "trust_policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": user_arn},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "attached_policy_arns": [policy_arn],
            },
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=UUID(workspace_id),
            discovery_run_id=discovery_run.id,
            resource_type="iam_policy",
            resource_id="policy-1",
            name="policy-1",
            arn=policy_arn,
            details={
                "policy_id": "p1",
                "policy_arn": policy_arn,
                "document": policy_document,
            },
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=UUID(workspace_id),
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
            workspace_id=UUID(workspace_id),
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
            workspace_id=UUID(workspace_id),
            discovery_run_id=discovery_run.id,
            resource_type="ec2_instance",
            resource_id="instance-1",
            name="instance-1",
            arn="arn:aws:ec2:us-east-1:000000000000:instance/i1",
            details={"instance_id": "i1", "arn": "arn:aws:ec2:us-east-1:000000000000:instance/i1"},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=UUID(workspace_id),
            discovery_run_id=discovery_run.id,
            resource_type="s3_bucket",
            resource_id="bucket-1",
            name="bucket-1",
            arn="arn:aws:s3:::bucket",
            details={"bucket_name": "bucket", "arn": "arn:aws:s3:::bucket"},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=UUID(workspace_id),
            discovery_run_id=discovery_run.id,
            resource_type="kms_key",
            resource_id="key-1",
            name="key-1",
            arn="arn:aws:kms:us-east-1:000000000000:key/key-1",
            details={"key_id": "key-1", "arn": "arn:aws:kms:us-east-1:000000000000:key/key-1"},
        )
    )
    db_session.add(
        CloudDiscoveredResourceModel(
            workspace_id=UUID(workspace_id),
            discovery_run_id=discovery_run.id,
            resource_type="lambda_function",
            resource_id="function-1",
            name="function-1",
            arn="arn:aws:lambda:us-east-1:000000000000:function:function-1",
            details={"function_name": "function-1", "arn": "arn:aws:lambda:us-east-1:000000000000:function:function-1"},
        )
    )
    await db_session.commit()

    build_response = await client.post(f"/api/v1/graph/workspaces/{workspace_id}/build", headers=headers)
    assert build_response.status_code == 200

    analyze_response = await client.post(f"/api/v1/attack-path/workspaces/{workspace_id}/analyze", headers=headers)
    assert analyze_response.status_code == 200
    analyze_body = analyze_response.json()
    assert analyze_body["path_count"] >= 5

    list_response = await client.get(f"/api/v1/attack-path/workspaces/{workspace_id}", headers=headers)
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["path_count"] >= 5
