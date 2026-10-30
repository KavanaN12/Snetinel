from types import SimpleNamespace

import pytest

from src.modules.iam_analysis.agent import (
    AgentAnalysis,
    AgentObservation,
    AutonomousIamAgent,
)
from src.modules.iam_analysis.remediation import RemediationExecution


def build_path():
    return SimpleNamespace(
        id="path-1",
        steps=[
            {"id": "user-node", "node_type": "iam_user", "external_id": "alice"},
            {"id": "role-node", "node_type": "iam_role", "external_id": "worker"},
            {"id": "bucket-node", "node_type": "s3_bucket", "external_id": "reports"},
        ],
        details={
            "edge_evidence": [
                {
                    "type": "ASSUME_ROLE",
                    "source": "user-node",
                    "target": "role-node",
                    "details": {},
                },
                {
                    "type": "CAN_ACCESS",
                    "source": "role-node",
                    "target": "bucket-node",
                    "details": {
                        "actions": ["s3:GetObject"],
                        "resource_arns": {
                            "s3:GetObject": "arn:aws:s3:::reports/*"
                        },
                    },
                },
            ]
        },
    )


def build_role_path():
    return SimpleNamespace(
        id="path-2",
        steps=[
            {"id": "role-node", "node_type": "iam_role", "external_id": "worker"},
            {"id": "bucket-node", "node_type": "s3_bucket", "external_id": "reports"},
        ],
        details={
            "edge_evidence": [
                {
                    "type": "CAN_ACCESS",
                    "source": "role-node",
                    "target": "bucket-node",
                    "details": {
                        "actions": ["s3:GetObject"],
                        "resource_arns": {
                            "s3:GetObject": "arn:aws:s3:::reports/*"
                        },
                    },
                }
            ]
        },
    )


class SequenceObserver:
    def __init__(self, observations):
        self.observations = iter(observations)

    async def __call__(self):
        return next(self.observations)


class SnapshotAnalyzer:
    async def __call__(self, observation):
        paths = observation.metadata["paths"]
        return AgentAnalysis(paths=paths, risk_scores={str(path.id): 80 for path in paths})


class RecordingExecutor:
    def __init__(self):
        self.plans = []

    def execute(self, plan):
        self.plans.append(plan)
        return RemediationExecution(
            status="applied",
            policy_name=f"deny-{len(self.plans)}",
            action=plan.action,
            resource_arn=plan.resource_arn,
            rollback={
                "operation": "delete_user_policy",
                "principal_parameter": "UserName",
                "principal_name": plan.principal_name,
                "policy_name": f"deny-{len(self.plans)}",
            },
            verified=True,
        )


@pytest.mark.asyncio
async def test_agent_replans_to_a_different_edge_and_verifies_after_recollection() -> None:
    path = build_path()
    user = SimpleNamespace(
        id="user-node",
        node_type="iam_user",
        external_id="alice",
        details={"arn": "arn:aws:iam::123456789012:user/alice"},
    )
    role = SimpleNamespace(
        id="role-node",
        node_type="iam_role",
        external_id="worker",
        details={"arn": "arn:aws:iam::123456789012:role/worker"},
    )
    bucket = SimpleNamespace(
        id="bucket-node",
        node_type="s3_bucket",
        external_id="reports",
        details={"arn": "arn:aws:s3:::reports"},
    )
    observations = [
        AgentObservation([user, role, bucket], [], {"paths": [path]}),
        AgentObservation([user, role, bucket], [], {"paths": [path]}),
        AgentObservation([user, role, bucket], [], {"paths": []}),
    ]
    executor = RecordingExecutor()
    agent = AutonomousIamAgent(
        observe=SequenceObserver(observations),
        analyze=SnapshotAnalyzer(),
        executor=executor,
        max_attempts=3,
    )

    result = await agent.run()

    assert result.status == "verified"
    assert [plan.action for plan in executor.plans] == [
        "sts:AssumeRole",
        "s3:GetObject",
    ]
    assert result.baseline_path_count == 1
    assert result.final_path_count == 0
    assert result.evaluation["replanning_attempts"] == 1
    assert result.evaluation["verification_success_rate"] == 0.5
    assert [event["stage"] for event in result.lifecycle].count("RE-PLAN") == 2


@pytest.mark.asyncio
async def test_agent_does_not_report_verified_while_other_attack_paths_remain() -> None:
    user_path = build_path()
    role_path = build_role_path()
    user = SimpleNamespace(
        id="user-node",
        node_type="iam_user",
        external_id="alice",
        details={"arn": "arn:aws:iam::123456789012:user/alice"},
    )
    role = SimpleNamespace(
        id="role-node",
        node_type="iam_role",
        external_id="worker",
        details={"arn": "arn:aws:iam::123456789012:role/worker"},
    )
    bucket = SimpleNamespace(
        id="bucket-node",
        node_type="s3_bucket",
        external_id="reports",
        details={"arn": "arn:aws:s3:::reports"},
    )
    observations = [
        AgentObservation([user, role, bucket], [], {"paths": [user_path, role_path]}),
        AgentObservation([user, role, bucket], [], {"paths": [role_path]}),
        AgentObservation([user, role, bucket], [], {"paths": []}),
    ]
    executor = RecordingExecutor()
    agent = AutonomousIamAgent(
        observe=SequenceObserver(observations),
        analyze=SnapshotAnalyzer(),
        executor=executor,
        max_attempts=2,
    )

    result = await agent.run()

    assert result.status == "verified"
    assert result.baseline_path_count == 2
    assert result.final_path_count == 0
    assert [plan.action for plan in executor.plans] == ["sts:AssumeRole", "s3:GetObject"]
    assert result.attempts[0]["remaining_attack_paths"] == 1
    assert result.attempts[1]["remaining_attack_paths"] == 0
    assert result.evaluation["replanning_attempts"] == 1
    assert any(
        event["stage"] == "RE-PLAN"
        and "other attack path(s) remain" in event.get("reason", "")
        for event in result.lifecycle
    )


@pytest.mark.asyncio
async def test_default_attempt_limit_can_replan_across_four_independent_paths() -> None:
    bucket = SimpleNamespace(
        id="bucket-node",
        node_type="s3_bucket",
        external_id="reports",
        details={"arn": "arn:aws:s3:::reports"},
    )
    users = [
        SimpleNamespace(
            id=f"user-node-{index}",
            node_type="iam_user",
            external_id=f"user-{index}",
            details={"arn": f"arn:aws:iam::123456789012:user/user-{index}"},
        )
        for index in range(4)
    ]
    paths = [
        SimpleNamespace(
            id=f"path-{index}",
            steps=[
                {"id": user.id, "node_type": "iam_user", "external_id": user.external_id},
                {"id": bucket.id, "node_type": "s3_bucket", "external_id": bucket.external_id},
            ],
            details={
                "edge_evidence": [
                    {
                        "type": "CAN_ACCESS",
                        "source": user.id,
                        "target": bucket.id,
                        "details": {
                            "actions": ["s3:GetObject"],
                            "resource_arns": {
                                "s3:GetObject": "arn:aws:s3:::reports/*"
                            },
                        },
                    }
                ]
            },
        )
        for index, user in enumerate(users)
    ]
    observations = [
        AgentObservation(users + [bucket], [], {"paths": paths[index:]})
        for index in range(5)
    ]
    executor = RecordingExecutor()
    agent = AutonomousIamAgent(
        observe=SequenceObserver(observations),
        analyze=SnapshotAnalyzer(),
        executor=executor,
    )

    result = await agent.run()

    assert result.status == "verified"
    assert result.baseline_path_count == 4
    assert result.final_path_count == 0
    assert len(executor.plans) == 4
    assert result.evaluation["replanning_attempts"] == 3
