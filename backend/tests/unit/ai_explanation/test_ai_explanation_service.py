import pytest

from src.modules.ai_explanation.services.ai_explanation_service import AIExplanationService


@pytest.mark.asyncio
async def test_explain_finding_returns_grounded_deterministic_summary():
    service = AIExplanationService()
    finding = {
        "id": "finding-1",
        "workspace_id": "workspace-1",
        "title": "IAM role assumption path",
        "description": "A user can assume a privileged role.",
        "severity": "high",
        "status": "open",
        "evidence_subgraph": {"attack_type": "iam_assume_role", "steps": ["iam_user", "iam_role"]},
        "affected_resource_ids": ["user-1", "role-1"],
    }

    result = await service.explain_finding(finding)

    assert result.summary.startswith("High-severity finding")
    assert "iam_assume_role" in result.summary
    assert result.confidence == "high"
    assert result.fallback_used is False
