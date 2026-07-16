import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.infrastructure.models import AttackPathModel
from src.modules.audit.infrastructure.models import AuditLogModel


@pytest.mark.asyncio
async def test_risk_scoring_dashboard_and_audit_flow(client, db_session: AsyncSession):
    # Register and authenticate a user.
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "riskflow@example.com", "password": "password123"},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "riskflow@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    workspace_response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Risk Workspace", "description": "demo"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    db_session.add(
        AttackPathModel(
            workspace_id=workspace_id,
            attack_type="iam_assume_role",
            steps=[
                {"id": "u1", "node_type": "iam_user", "name": "alice"},
                {"id": "r1", "node_type": "iam_role", "name": "AdminRole"},
            ],
            details={"edge_type": "ASSUME_ROLE"},
        )
    )
    await db_session.commit()

    evaluate_response = await client.post(
        f"/api/v1/risk-scoring/workspaces/{workspace_id}/evaluate",
        headers=headers,
    )
    assert evaluate_response.status_code == 200
    findings = evaluate_response.json()["findings"]
    assert len(findings) == 1

    explain_response = await client.post(
        "/api/v1/ai-explanation/explain",
        json=findings[0],
        headers=headers,
    )
    assert explain_response.status_code == 200
    assert "High-severity finding" in explain_response.json()["summary"]

    dashboard_response = await client.get(
        f"/api/v1/dashboard/workspaces/{workspace_id}/summary",
        headers=headers,
    )
    assert dashboard_response.status_code == 200
    body = dashboard_response.json()
    assert body["finding_counts"]["total"] == 1
    assert body["severity_counts"]["high"] == 1

    audit_logs_result = await db_session.execute(select(AuditLogModel))
    audit_logs = audit_logs_result.scalars().all()
    assert len(audit_logs) >= 1
