from datetime import datetime, timezone
from uuid import UUID

import pytest

from src.modules.iam_analysis.infrastructure.models import IamAgentRunModel


@pytest.mark.asyncio
async def test_iam_agent_history_is_authenticated_and_returns_persisted_contract(client, db_session):
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "iam-agent@example.com", "password": "password123"},
    )
    assert registration.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "iam-agent@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "IAM Agent Workspace", "description": "agent history API test"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = UUID(workspace_response.json()["id"])

    db_session.add(
        IamAgentRunModel(
            workspace_id=workspace_id,
            status="verified",
            lifecycle=[
                {
                    "stage": "REPORT",
                    "status": "completed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "run_status": "verified",
                }
            ],
            attempts=[],
            baseline_path_count=2,
            final_path_count=0,
            evaluation={
                "baseline_attack_paths": 2,
                "final_attack_paths": 0,
                "attack_path_reduction_percent": 100.0,
                "baseline_average_risk": 80.0,
                "final_average_risk": None,
                "risk_reduction_percent": 100.0,
                "remediation_success_rate": None,
                "verification_success_rate": None,
                "unnecessary_permission_changes": 0,
                "replanning_attempts": 0,
                "execution_time_seconds": 1.25,
            },
        )
    )
    await db_session.commit()

    unauthenticated = await client.get(
        f"/api/v1/iam-agent/workspaces/{workspace_id}/runs"
    )
    assert unauthenticated.status_code == 401

    invalid_run_request = await client.post(
        f"/api/v1/iam-agent/workspaces/{workspace_id}/run",
        json={"max_attempts": 6},
        headers=headers,
    )
    assert invalid_run_request.status_code == 422

    history = await client.get(
        f"/api/v1/iam-agent/workspaces/{workspace_id}/runs",
        headers=headers,
    )
    assert history.status_code == 200
    body = history.json()
    assert len(body) == 1
    assert body[0]["status"] == "verified"
    assert body[0]["baseline_path_count"] == 2
    assert body[0]["final_path_count"] == 0
    assert body[0]["evaluation"]["attack_path_reduction_percent"] == 100.0
    assert body[0]["lifecycle"][0]["stage"] == "REPORT"
