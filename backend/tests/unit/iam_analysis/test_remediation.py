import json
from types import SimpleNamespace

import pytest

from src.modules.iam_analysis.remediation import (
    LocalStackEndpointError,
    LocalStackIamExecutor,
    RemediationPlan,
    RemediationPlanner,
)


class FakeIamClient:
    def __init__(self) -> None:
        self.policies = {}

    def put_user_policy(self, UserName, PolicyName, PolicyDocument):
        self.policies[(UserName, PolicyName)] = json.loads(PolicyDocument)

    def get_user_policy(self, UserName, PolicyName):
        return {"PolicyDocument": self.policies[(UserName, PolicyName)]}

    def delete_user_policy(self, UserName, PolicyName):
        self.policies.pop((UserName, PolicyName), None)


def test_planner_selects_a_scoped_action_from_path_evidence() -> None:
    user = SimpleNamespace(
        id="user-node",
        node_type="iam_user",
        external_id="alice",
        details={"arn": "arn:aws:iam::123456789012:user/alice"},
    )
    bucket = SimpleNamespace(
        id="bucket-node",
        node_type="s3_bucket",
        external_id="reports",
        details={"arn": "arn:aws:s3:::reports"},
    )
    path = SimpleNamespace(
        id="path-1",
        details={
            "edge_evidence": [
                {
                    "type": "CAN_ACCESS",
                    "source": "user-node",
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

    plan = RemediationPlanner().select(path, [user, bucket])

    assert plan is not None
    assert plan.principal_type == "user"
    assert plan.principal_name == "alice"
    assert plan.action == "s3:GetObject"
    assert plan.resource_arn == "arn:aws:s3:::reports/*"


def test_executor_rejects_non_localstack_endpoint_before_mutating() -> None:
    iam = FakeIamClient()
    executor = LocalStackIamExecutor(iam, "https://aws.example.com")
    plan = RemediationPlan(
        principal_type="user",
        principal_name="alice",
        action="s3:GetObject",
        resource_arn="arn:aws:s3:::reports/*",
        strategy="add_targeted_explicit_deny",
        reason="test",
        operational_impact="test",
    )

    with pytest.raises(LocalStackEndpointError):
        executor.execute(plan)
    assert iam.policies == {}


def test_executor_applies_verifies_and_rolls_back_inline_deny() -> None:
    iam = FakeIamClient()
    executor = LocalStackIamExecutor(iam, "http://localhost:4566")
    executor.check_ready = lambda: None
    plan = RemediationPlan(
        principal_type="user",
        principal_name="alice",
        action="s3:GetObject",
        resource_arn="arn:aws:s3:::reports/*",
        strategy="add_targeted_explicit_deny",
        reason="test",
        operational_impact="test",
    )

    execution = executor.execute(plan)
    assert execution.status == "applied"
    assert execution.verified
    assert iam.policies[("alice", execution.policy_name)]["Statement"][0]["Effect"] == "Deny"

    executor.rollback(execution)
    assert ("alice", execution.policy_name) not in iam.policies
