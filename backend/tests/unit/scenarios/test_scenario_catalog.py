from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from src.modules.iam_analysis.remediation import LocalStackEndpointError
from src.modules.scenarios.catalog import SCENARIOS, SCENARIOS_BY_ID
from src.modules.scenarios.service import ScenarioService


def test_catalog_scenario_ids_are_unique_and_have_machine_assertions():
    assert len(SCENARIOS_BY_ID) == len(SCENARIOS)
    assert {scenario.difficulty for scenario in SCENARIOS} == {
        "easy",
        "intermediate",
        "advanced",
    }
    assert all(scenario.expected_min_paths >= 0 for scenario in SCENARIOS)
    assert all(
        scenario.expected_max_paths is None
        or scenario.expected_max_paths >= scenario.expected_min_paths
        for scenario in SCENARIOS
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item.scenario_id)
def test_scenario_manifest_namespaces_every_resource_and_policy(scenario):
    workspace_id = uuid4()
    run_id = uuid4()
    manifest = ScenarioService._manifest_for(
        scenario,
        workspace_id.hex[:8],
        run_id,
    )
    prefix = f"sentinel-{scenario.scenario_id[:12]}-{workspace_id.hex[:8]}"

    assert manifest["users"]
    assert manifest["bucket_name"].startswith(prefix)
    assert all(name.startswith(prefix) for name in manifest["users"])
    assert all(name.startswith(prefix) for name in manifest["roles"])
    assert len(manifest["resource_keys"]) == (
        len(manifest["users"]) + len(manifest["roles"]) + 1
    )
    assert all(item["policy_name"].startswith("Sentinel-") for item in manifest["inline_policies"])
    assert len(
        {
            (item["principal_type"], item["principal_name"], item["policy_name"])
            for item in manifest["inline_policies"]
        }
    ) == len(manifest["inline_policies"])
    if scenario.topology == "long_role_chain":
        assert len(manifest["roles"]) == 5
        assert len(
            [
                policy
                for policy in manifest["inline_policies"]
                if policy["principal_type"] == "role"
            ]
        ) == 5
    if scenario.topology == "role_cycle":
        assert len(manifest["roles"]) == 2
        assert {
            (policy["principal_type"], policy["principal_name"])
            for policy in manifest["inline_policies"]
        } == {
            ("user", manifest["users"][0]),
            ("role", manifest["roles"][0]),
            ("role", manifest["roles"][1]),
        }


def test_observed_vulnerabilities_are_derived_from_attack_path_evidence():
    paths = [
        SimpleNamespace(
            attack_type="s3_access",
            steps=[
                {"node_type": "iam_user", "external_id": "entry-a"},
                {"node_type": "iam_role"},
                {"node_type": "s3_bucket"},
            ],
            details={
                "edge_evidence": [
                    {"details": {"actions": ["s3:PutObject"]}},
                ]
            },
        ),
        SimpleNamespace(
            attack_type="s3_access",
            steps=[
                {"node_type": "iam_user", "external_id": "entry-b"},
                {"node_type": "s3_bucket"},
            ],
            details={"edge_evidence": []},
        ),
    ]

    observed = ScenarioService._observed_vulnerabilities(paths)

    assert observed == [
        "assume_role_escalation",
        "excessive_s3_permissions",
        "multiple_attack_paths",
        "multiple_entry_points",
        "s3_access",
    ]


@pytest.mark.parametrize(
    ("expected", "actual", "matches"),
    [
        ("none", [], True),
        ("none", ["medium"], False),
        ("high or critical", ["medium"], False),
        ("high or critical", ["critical"], True),
        ("medium or high or critical", ["medium"], True),
    ],
)
def test_risk_expectations_match_declared_severity_range(expected, actual, matches):
    assert ScenarioService._risk_matches_expectation(expected, actual) is matches


@pytest.mark.asyncio
async def test_post_remediation_assertion_reports_phase_specific_expectations():
    workspace_id = uuid4()
    run = SimpleNamespace(
        workspace_id=workspace_id,
        resource_manifest={"bucket_name": "scenario-data"},
        expected_results={
            "expected_resources": ["iam_user", "s3_bucket"],
            "expected_vulnerabilities": ["s3_access"],
            "expected_min_paths": 1,
            "expected_max_paths": None,
            "expected_risk": "high or critical",
        },
        actual_results={},
    )

    class ScenarioRepository:
        async def get(self, run_id):
            return run

        async def set_actual_results(self, model, results):
            model.actual_results = results

    class Session:
        async def commit(self):
            pass

    service = ScenarioService(
        session=Session(),
        workspace_repository=None,
        scenario_repository=ScenarioRepository(),
    )
    service._ensure_workspace = AsyncMock()

    assertion = await service.record_assertion(
        workspace_id,
        "owner",
        uuid4(),
        phase="post_remediation",
        nodes=[
            SimpleNamespace(external_id="user", node_type="iam_user"),
            SimpleNamespace(external_id="scenario-data", node_type="s3_bucket"),
        ],
        paths=[],
    )

    assert assertion["passed"] is True
    assert assertion["expected"]["expected_min_paths"] == 0
    assert assertion["expected"]["expected_vulnerabilities"] == []
    assert assertion["actual"]["attack_path_count_matches_expectation"] is True
    assert assertion["actual"]["vulnerabilities_match_expectation"] is True
    assert assertion["actual"]["risk_matches_expectation"] is True


def test_scenario_fixture_refuses_non_localstack_endpoint():
    service = ScenarioService(
        session=None,
        workspace_repository=None,
        scenario_repository=None,
        endpoint_url="https://aws.amazon.com",
    )

    with pytest.raises(LocalStackEndpointError):
        service._localstack_clients()
