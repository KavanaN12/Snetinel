from __future__ import annotations

import hashlib
import json
import ipaddress
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import uuid4

from src.modules.iam_analysis.policy_evaluator import IamPolicyEvaluator


class LocalStackEndpointError(RuntimeError):
    pass


class RemediationVerificationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RemediationPlan:
    principal_type: str
    principal_name: str
    action: str
    resource_arn: str
    strategy: str
    reason: str
    operational_impact: str


@dataclass(frozen=True, slots=True)
class RemediationExecution:
    status: str
    policy_name: str
    action: str
    resource_arn: str
    rollback: dict[str, str]
    verified: bool


class RemediationPlanner:
    """Chooses a narrowly scoped deny from evidence in a persisted attack path."""

    def select(
        self,
        path: Any,
        nodes: list[Any],
        excluded_changes: set[str] | None = None,
    ) -> RemediationPlan | None:
        nodes_by_id = {str(node.id): node for node in nodes}
        evidence = (path.details or {}).get("edge_evidence", [])
        if not isinstance(evidence, list):
            return None

        candidates = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            edge_type = item.get("type")
            source = nodes_by_id.get(str(item.get("source")))
            target = nodes_by_id.get(str(item.get("target")))
            if source is None or target is None:
                continue
            if source.node_type not in {"iam_user", "iam_role", "iam_group"}:
                continue
            actions = (item.get("details") or {}).get("actions", [])
            if edge_type == "ASSUME_ROLE":
                actions = ["sts:AssumeRole"]
            resource_arns = (item.get("details") or {}).get("resource_arns", {})
            if not isinstance(actions, list):
                continue
            for action in actions:
                if not isinstance(action, str) or "*" in action:
                    continue
                resource_arn = resource_arns.get(action)
                if edge_type == "ASSUME_ROLE":
                    resource_arn = (target.details or {}).get("arn")
                elif source.node_type == "iam_group" and target.node_type != "iam_role":
                    continue
                if not isinstance(resource_arn, str) or not resource_arn.startswith("arn:"):
                    continue
                change_key = (
                    f"{source.node_type.removeprefix('iam_')}:{source.external_id}:"
                    f"{action}:{resource_arn}"
                )
                if change_key in (excluded_changes or set()):
                    continue
                candidates.append(
                    RemediationPlan(
                        principal_type=source.node_type.removeprefix("iam_"),
                        principal_name=source.external_id,
                        action=action,
                        resource_arn=resource_arn,
                        strategy="add_targeted_explicit_deny",
                        reason=f"Blocks the observed {action} edge in attack path {path.id}.",
                        operational_impact=(
                            f"Denies {action} on {resource_arn} for {source.node_type.removeprefix('iam_')} "
                            f"{source.external_id}; other actions and resources are unchanged."
                        ),
                    )
                )
        return candidates[0] if candidates else None


class LocalStackIamExecutor:
    """Applies only targeted IAM changes to a verified local LocalStack endpoint."""

    _ALLOWED_PRINCIPAL_TYPES = {"user", "role", "group"}
    _IAM_POLICY_OPERATIONS = {
        "user": ("put_user_policy", "get_user_policy", "delete_user_policy", "UserName"),
        "role": ("put_role_policy", "get_role_policy", "delete_role_policy", "RoleName"),
        "group": ("put_group_policy", "get_group_policy", "delete_group_policy", "GroupName"),
    }

    def __init__(self, iam_client: Any, endpoint_url: str, *, timeout_seconds: float = 3.0) -> None:
        self._iam = iam_client
        self._endpoint_url = endpoint_url
        self._timeout_seconds = timeout_seconds

    def execute(self, plan: RemediationPlan) -> RemediationExecution:
        self.check_ready()
        if plan.principal_type not in self._ALLOWED_PRINCIPAL_TYPES:
            raise ValueError(f"Unsupported IAM principal type: {plan.principal_type}")
        if not plan.action or "*" in plan.action or ":" not in plan.action:
            raise ValueError("Remediation requires one exact IAM action")
        if not plan.resource_arn.startswith("arn:") or plan.resource_arn == "*":
            raise ValueError("Remediation requires a specific AWS resource ARN")

        put_operation, get_operation, _, identity_parameter = self._IAM_POLICY_OPERATIONS[
            plan.principal_type
        ]
        policy_name = f"SentinelContainment-{uuid4().hex[:16]}"
        principal_parameter = {identity_parameter: plan.principal_name}
        deny_statement = {
            "Sid": f"Sentinel{hashlib.sha256((plan.action + plan.resource_arn).encode()).hexdigest()[:12]}",
            "Effect": "Deny",
            "Action": plan.action,
            "Resource": plan.resource_arn,
        }
        policy_document = {"Version": "2012-10-17", "Statement": [deny_statement]}
        getattr(self._iam, put_operation)(
            **principal_parameter,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document, separators=(",", ":")),
        )
        observed = getattr(self._iam, get_operation)(
            **principal_parameter,
            PolicyName=policy_name,
        ).get("PolicyDocument")
        verification = IamPolicyEvaluator().evaluate(
            action=plan.action,
            resource=plan.resource_arn,
            policies=[observed] if isinstance(observed, (dict, str)) else [],
        )
        if verification.decision != "EXPLICIT_DENY":
            getattr(self._iam, self._IAM_POLICY_OPERATIONS[plan.principal_type][2])(
                **principal_parameter,
                PolicyName=policy_name,
            )
            raise RemediationVerificationError(
                "LocalStack did not return the expected explicit deny after policy update"
            )

        return RemediationExecution(
            status="applied",
            policy_name=policy_name,
            action=plan.action,
            resource_arn=plan.resource_arn,
            rollback={
                "operation": self._IAM_POLICY_OPERATIONS[plan.principal_type][2],
                "principal_parameter": identity_parameter,
                "principal_name": plan.principal_name,
                "policy_name": policy_name,
            },
            verified=True,
        )

    def rollback(self, execution: RemediationExecution) -> None:
        self.check_ready()
        operation = execution.rollback.get("operation")
        if operation not in {
            "delete_user_policy",
            "delete_role_policy",
            "delete_group_policy",
        }:
            raise ValueError("Rollback record does not identify a safe inline-policy deletion")
        parameter_name = execution.rollback.get("principal_parameter")
        principal_name = execution.rollback.get("principal_name")
        policy_name = execution.rollback.get("policy_name")
        if not parameter_name or not principal_name or not policy_name:
            raise ValueError("Rollback record is incomplete")
        getattr(self._iam, operation)(
            **{parameter_name: principal_name},
            PolicyName=policy_name,
        )

    def check_ready(self) -> None:
        parsed = urlsplit(self._endpoint_url)
        hostname = (parsed.hostname or "").casefold()
        allowed_host = hostname in {"localhost", "127.0.0.1", "::1", "localstack"}
        if not allowed_host or parsed.scheme != "http" or parsed.port != 4566:
            raise LocalStackEndpointError(
                "IAM remediation is restricted to http://localhost:4566 or the LocalStack compose service"
            )
        if hostname not in {"localhost", "localstack"}:
            try:
                if not ipaddress.ip_address(hostname).is_loopback:
                    raise LocalStackEndpointError("IAM remediation endpoint is not loopback")
            except ValueError as exc:
                raise LocalStackEndpointError("IAM remediation endpoint is not loopback") from exc

        health_url = f"{self._endpoint_url.rstrip('/')}/_localstack/health"
        try:
            with urlopen(health_url, timeout=self._timeout_seconds) as response:
                if response.status != 200:
                    raise LocalStackEndpointError(
                        f"LocalStack health check returned HTTP {response.status}"
                    )
                health = json.loads(response.read())
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LocalStackEndpointError(
                f"Unable to verify LocalStack health at {health_url}: {exc}"
            ) from exc
        iam_status = (health.get("services") or {}).get("iam")
        if iam_status not in {"available", "running"}:
            raise LocalStackEndpointError(
                f"LocalStack IAM service is not ready (reported status: {iam_status!r})"
            )
