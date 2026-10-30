from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    scenario_id: str
    name: str
    difficulty: str
    description: str
    topology: str
    expected_resources: tuple[str, ...]
    expected_vulnerabilities: tuple[str, ...]
    expected_attack_paths: str
    expected_min_paths: int
    expected_max_paths: int | None
    expected_risk: str
    expected_remediation: str
    expected_post_state: str

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        return {
            key: list(item) if isinstance(item, tuple) else item
            for key, item in value.items()
        }


SCENARIOS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        scenario_id="secure-iam",
        name="Secure IAM baseline",
        difficulty="easy",
        description="A user, role, and S3 bucket with no permission or trust path to the bucket.",
        topology="secure",
        expected_resources=("iam_user", "iam_role", "s3_bucket"),
        expected_vulnerabilities=(),
        expected_attack_paths="0",
        expected_min_paths=0,
        expected_max_paths=0,
        expected_risk="none",
        expected_remediation="none",
        expected_post_state="No attack paths before or after analysis.",
    ),
    ScenarioDefinition(
        scenario_id="excessive-s3-access",
        name="Excessive S3 permissions",
        difficulty="easy",
        description="A user can read and write a sensitive S3 bucket directly.",
        topology="direct_s3",
        expected_resources=("iam_user", "s3_bucket"),
        expected_vulnerabilities=("excessive_s3_permissions",),
        expected_attack_paths="1 or more",
        expected_min_paths=1,
        expected_max_paths=None,
        expected_risk="high or critical",
        expected_remediation="Add a targeted explicit deny for the observed S3 action and bucket ARN.",
        expected_post_state="The agent removes the observed access path or reports a bounded failure.",
    ),
    ScenarioDefinition(
        scenario_id="direct-assume-role",
        name="Direct role escalation",
        difficulty="easy",
        description="A user can assume a trusted role that can access a sensitive S3 bucket.",
        topology="direct_role",
        expected_resources=("iam_user", "iam_role", "s3_bucket"),
        expected_vulnerabilities=("assume_role_escalation", "s3_access"),
        expected_attack_paths="1 or more",
        expected_min_paths=1,
        expected_max_paths=None,
        expected_risk="medium or high or critical",
        expected_remediation="Add a targeted explicit deny on an observed role-assumption or S3-access edge.",
        expected_post_state="The agent re-discovers the account and verifies that all observed paths are removed.",
    ),
    ScenarioDefinition(
        scenario_id="explicit-deny",
        name="Explicit Deny protection",
        difficulty="easy",
        description="An Allow is overridden by an explicit Deny for the sensitive bucket.",
        topology="explicit_deny",
        expected_resources=("iam_user", "s3_bucket"),
        expected_vulnerabilities=(),
        expected_attack_paths="0",
        expected_min_paths=0,
        expected_max_paths=0,
        expected_risk="none",
        expected_remediation="none",
        expected_post_state="The explicit Deny remains and no access path is reported.",
    ),
    ScenarioDefinition(
        scenario_id="multi-hop-role-chain",
        name="Multi-hop role escalation",
        difficulty="intermediate",
        description="A user assumes a chain of three roles before reaching sensitive S3 data.",
        topology="role_chain",
        expected_resources=("iam_user", "iam_role", "s3_bucket"),
        expected_vulnerabilities=("multi_hop_assume_role", "s3_access"),
        expected_attack_paths="1 or more",
        expected_min_paths=1,
        expected_max_paths=None,
        expected_risk="medium or high or critical",
        expected_remediation="Target an observed edge; remaining paths are re-analyzed before another attempt.",
        expected_post_state="The run is verified only if fresh analysis finds zero paths.",
    ),
    ScenarioDefinition(
        scenario_id="long-role-chain",
        name="Long role escalation chain",
        difficulty="advanced",
        description="A user assumes five consecutive IAM roles before reaching sensitive S3 data.",
        topology="long_role_chain",
        expected_resources=("iam_user", "iam_role", "s3_bucket"),
        expected_vulnerabilities=("multi_hop_assume_role", "s3_access"),
        expected_attack_paths="1 or more",
        expected_min_paths=1,
        expected_max_paths=None,
        expected_risk="medium or high or critical",
        expected_remediation="Revoke an observed role-assumption or S3-access edge and re-analyze the chain.",
        expected_post_state="The run is verified only if fresh analysis finds zero paths.",
    ),
    ScenarioDefinition(
        scenario_id="shared-privileged-role",
        name="Multiple users, shared privileged role",
        difficulty="intermediate",
        description="Two independent users can assume the same role and access the same sensitive bucket.",
        topology="shared_role",
        expected_resources=("iam_user", "iam_role", "s3_bucket"),
        expected_vulnerabilities=("multiple_entry_points", "s3_access"),
        expected_attack_paths="1 or more per reachable user",
        expected_min_paths=2,
        expected_max_paths=None,
        expected_risk="medium or high or critical",
        expected_remediation="Targeted changes are verified against every remaining path in the workspace.",
        expected_post_state="The run is verified only if fresh analysis finds zero paths.",
    ),
    ScenarioDefinition(
        scenario_id="circular-role-trust",
        name="Circular IAM role trust",
        difficulty="intermediate",
        description="Two roles trust each other; a user can enter the cycle and reach sensitive S3 data.",
        topology="role_cycle",
        expected_resources=("iam_user", "iam_role", "s3_bucket"),
        expected_vulnerabilities=("multi_hop_assume_role", "s3_access"),
        expected_attack_paths="1 or more",
        expected_min_paths=1,
        expected_max_paths=None,
        expected_risk="medium or high or critical",
        expected_remediation="Remove an observed entry or access edge, then verify the cycle is no longer reachable.",
        expected_post_state="The run is verified only if fresh analysis finds zero paths.",
    ),
    ScenarioDefinition(
        scenario_id="multiple-s3-paths",
        name="Multiple paths to sensitive S3",
        difficulty="intermediate",
        description="Independent users and roles expose multiple routes to a shared sensitive bucket.",
        topology="multiple_paths",
        expected_resources=("iam_user", "iam_role", "s3_bucket"),
        expected_vulnerabilities=("multiple_attack_paths", "s3_access"),
        expected_attack_paths="multiple",
        expected_min_paths=2,
        expected_max_paths=None,
        expected_risk="medium or high or critical",
        expected_remediation="The bounded agent selects an observed edge and replans against residual paths.",
        expected_post_state="The run is verified only if fresh analysis finds zero paths.",
    ),
)

SCENARIOS_BY_ID = {scenario.scenario_id: scenario for scenario in SCENARIOS}
