from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    score: int
    severity: str
    factors: dict[str, float]
    evidence: dict[str, Any]


class DeterministicRiskEngine:
    """Scores only observed path evidence; missing context remains explicit."""

    def assess(self, attack_type: str, steps: list[dict], details: dict[str, Any]) -> RiskAssessment:
        identity = steps[0].get("node_type") if steps else None
        target = steps[-1].get("node_type") if steps else None
        edge_evidence = details.get("edge_evidence", [])
        if not isinstance(edge_evidence, list):
            edge_evidence = []
        actions = sorted(
            {
                str(action)
                for evidence in edge_evidence
                if isinstance(evidence, dict)
                for action in (evidence.get("details") or {}).get("actions", [])
            }
        )

        exposure = 0.75 if identity == "iam_user" else 0.6 if identity == "iam_role" else 0.4
        if any((evidence.get("details") or {}).get("cross_account") for evidence in edge_evidence):
            exposure = 1.0
        breadth = max((self._action_risk(action) for action in actions), default=0.4)
        sensitivity = {
            "kms_key": 0.95,
            "s3_bucket": 0.75,
            "lambda_function": 0.8,
            "ec2_instance": 0.7,
            "iam_role": 0.9,
        }.get(target, 0.5)
        effort = details.get("algorithms", {}).get("effort_cost")
        if effort is None:
            effort = max(len(steps) - 1, 1)
        exploitability = 1.0 / (1.0 + max(float(effort), 0.0))

        factors = {
            "identity_exposure": exposure,
            "privilege_breadth": breadth,
            "resource_sensitivity": sensitivity,
            "exploitability": exploitability,
        }
        score = round(
            exposure * 30
            + breadth * 25
            + sensitivity * 25
            + exploitability * 20
        )
        severity = "critical" if score >= 85 else "high" if score >= 65 else "medium" if score >= 40 else "low"
        evidence = {
            "score": score,
            "severity": severity,
            "factors": factors,
            "attack_type": attack_type,
            "observed_actions": actions,
            "resource_sensitivity_basis": (
                "resource type" if target in {"kms_key", "s3_bucket", "lambda_function", "ec2_instance", "iam_role"}
                else "unknown resource type"
            ),
        }
        return RiskAssessment(score, severity, factors, evidence)

    @staticmethod
    def _action_risk(action: str) -> float:
        normalized = action.casefold()
        if normalized in {"*", "*:*"} or normalized.endswith(":*"):
            return 1.0
        if normalized.startswith(("iam:", "sts:", "kms:")):
            return 0.9
        if any(token in normalized for token in ("delete", "put", "update", "write", "attach", "create")):
            return 0.8
        if any(token in normalized for token in ("get", "list", "describe", "read")):
            return 0.6
        return 0.45
