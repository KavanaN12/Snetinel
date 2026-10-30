from types import SimpleNamespace

import pytest

from src.modules.risk_scoring.services.risk_scoring_service import RiskScoringService


class StubAttackPathRepository:
    def __init__(self, attack_paths):
        self._attack_paths = attack_paths

    async def list_for_workspace(self, workspace_id):
        return self._attack_paths


class StubWorkspaceRepository:
    def __init__(self, workspace):
        self._workspace = workspace

    async def get_by_id(self, workspace_id):
        return self._workspace


@pytest.mark.asyncio
async def test_generate_findings_from_attack_paths_is_deterministic():
    workspace = SimpleNamespace(id="workspace-1", owner_id="user-1")
    attack_path = SimpleNamespace(
        id="attack-1",
        workspace_id="workspace-1",
        attack_type="iam_assume_role",
        steps=[
            {"id": "u1", "node_type": "iam_user", "name": "alice"},
            {"id": "r1", "node_type": "iam_role", "name": "AdminRole"},
        ],
        details={"edge_type": "ASSUME_ROLE"},
    )

    service = RiskScoringService(
        workspace_repository=StubWorkspaceRepository(workspace),
        attack_path_repository=StubAttackPathRepository([attack_path]),
        finding_repository=None,
    )

    result = await service.generate_findings("workspace-1", "user-1")

    assert result.finding_count == 1
    finding = result.findings[0]
    assert finding.severity == "high"
    assert finding.status == "open"
    assert finding.affected_resource_ids == ["u1", "r1"]
    assert finding.evidence_subgraph["attack_type"] == "iam_assume_role"
    assert finding.evidence_subgraph["risk_assessment"]["score"] == 65
    assert finding.evidence_subgraph["risk_assessment"]["severity"] == "high"


def test_deterministic_risk_engine_scores_sensitive_wildcard_access_higher():
    from src.modules.risk_scoring.risk_engine import DeterministicRiskEngine

    engine = DeterministicRiskEngine()
    broad = engine.assess(
        "kms_access",
        [
            {"node_type": "iam_user"},
            {"node_type": "kms_key"},
        ],
        {
            "algorithms": {"effort_cost": 1},
            "edge_evidence": [
                {"details": {"actions": ["kms:*"], "cross_account": True}}
            ],
        },
    )
    narrow = engine.assess(
        "s3_access",
        [
            {"node_type": "iam_user"},
            {"node_type": "s3_bucket"},
        ],
        {
            "algorithms": {"effort_cost": 4},
            "edge_evidence": [
                {"details": {"actions": ["s3:GetObject"], "cross_account": False}}
            ],
        },
    )

    assert broad.score > narrow.score
    assert broad.severity == "critical"
    assert broad.evidence["observed_actions"] == ["kms:*"]
