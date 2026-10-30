from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import boto3
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.infrastructure.models import AttackPathModel
from src.modules.discovery.infrastructure.models import (
    CloudDiscoveredResourceModel,
    DiscoveryRunModel,
)
from src.modules.graph.infrastructure.models import GraphEdgeModel, GraphNodeModel
from src.modules.iam_analysis.infrastructure.models import IamAgentRunModel
from src.modules.iam_analysis.remediation import LocalStackIamExecutor
from src.modules.risk_scoring.infrastructure.models import FindingModel
from src.modules.risk_scoring.risk_engine import DeterministicRiskEngine
from src.modules.scenarios.catalog import SCENARIOS, SCENARIOS_BY_ID
from src.modules.scenarios.repositories import ScenarioRunRepository
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository
from src.shared.config.settings import get_settings


class ScenarioConflictError(RuntimeError):
    pass


class ScenarioService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        workspace_repository: WorkspaceRepository,
        scenario_repository: ScenarioRunRepository,
        endpoint_url: str | None = None,
    ) -> None:
        self._session = session
        self._workspaces = workspace_repository
        self._scenarios = scenario_repository
        self._settings = get_settings()
        self._endpoint_url = endpoint_url or self._settings.AWS_ENDPOINT_URL

    @staticmethod
    def list_catalog() -> list[dict[str, object]]:
        return [scenario.to_dict() for scenario in SCENARIOS]

    async def list_runs(self, workspace_id: UUID, owner_id: str) -> list:
        await self._ensure_workspace(workspace_id, owner_id)
        return await self._scenarios.list_for_workspace(workspace_id)

    async def load(self, workspace_id: UUID, owner_id: str, scenario_id: str):
        workspace = await self._ensure_workspace(workspace_id, owner_id)
        scenario = SCENARIOS_BY_ID.get(scenario_id)
        if scenario is None:
            raise ValueError(f"Unknown or unsupported scenario: {scenario_id}")
        if await self._scenarios.active_for_workspace(workspace_id):
            raise ScenarioConflictError("Reset the active scenario before loading another one.")
        if await self._has_existing_workspace_data(workspace_id):
            raise ScenarioConflictError(
                "Scenarios require a dedicated empty workspace. Existing workspace data was preserved."
            )

        clients = self._localstack_clients()
        suffix = UUID(str(workspace.id)).hex[:8]
        run = await self._scenarios.create(
            workspace_id=workspace.id,
            scenario_id=scenario.scenario_id,
            resource_manifest={},
            expected_results={},
        )
        run.status = "seeding"
        manifest = self._manifest_for(scenario, suffix, run.id)
        run.resource_manifest = manifest
        run.expected_results = self._expected_results(scenario, manifest)
        await self._session.commit()

        try:
            self._seed(clients, scenario.topology, manifest, str(workspace.id), str(run.id))
        except Exception:
            run.status = "failed"
            await self._session.commit()
            raise

        run.status = "loaded"
        await self._session.commit()
        return run

    async def reset(self, workspace_id: UUID, owner_id: str, run_id: UUID):
        await self._ensure_workspace(workspace_id, owner_id)
        run = await self._scenarios.get(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Scenario run was not found in this workspace.")
        if run.status == "reset":
            return run

        clients = self._localstack_clients()
        remediation_policies = await self._remediation_policies(workspace_id)
        principal_prefix = (
            f"sentinel-{run.scenario_id[:12]}-{UUID(str(run.workspace_id)).hex[:8]}"
        )
        for policy in remediation_policies:
            if policy["principal_name"].startswith(principal_prefix):
                policy["policy_name"] = policy["rollback"]["policy_name"]
                run.resource_manifest.setdefault("inline_policies", []).append(policy)
        self._delete_fixture_resources(clients, run.resource_manifest)
        for model in (
            GraphEdgeModel,
            GraphNodeModel,
            AttackPathModel,
            FindingModel,
            IamAgentRunModel,
            CloudDiscoveredResourceModel,
            DiscoveryRunModel,
        ):
            await self._session.execute(
                delete(model).where(model.workspace_id == workspace_id)
            )
        await self._scenarios.mark_reset(run)
        await self._session.commit()
        return run

    async def record_assertion(
        self,
        workspace_id: UUID,
        owner_id: str,
        run_id: UUID,
        *,
        phase: str,
        nodes: list,
        paths: list,
    ):
        await self._ensure_workspace(workspace_id, owner_id)
        run = await self._scenarios.get(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise ValueError("Scenario run was not found in this workspace.")
        if phase not in {"baseline", "post_remediation"}:
            raise ValueError("phase must be baseline or post_remediation")
        expected = dict(run.expected_results)
        if phase == "post_remediation":
            expected.update(
                expected_attack_paths="0",
                expected_min_paths=0,
                expected_max_paths=0,
                expected_vulnerabilities=[],
                expected_risk="none",
            )
        path_count = len(paths)
        min_paths = int(expected["expected_min_paths"])
        max_paths = expected.get("expected_max_paths")
        count_passed = path_count >= min_paths and (
            max_paths is None or path_count <= int(max_paths)
        )
        names = {node.external_id for node in nodes}
        bucket_name = run.resource_manifest.get("bucket_name")
        observed_bucket_paths = [
            path
            for path in paths
            if any(step.get("external_id") == bucket_name for step in path.steps)
        ]
        if bucket_name and expected["expected_min_paths"] > 0:
            count_passed = count_passed and bool(observed_bucket_paths)
        actual_resource_types = {node.node_type for node in nodes}
        expected_resource_types = set(expected["expected_resources"])
        resources_match = expected_resource_types.issubset(actual_resource_types)
        observed_vulnerabilities = self._observed_vulnerabilities(paths)
        vulnerability_match = (
            set(observed_vulnerabilities)
            == set(expected["expected_vulnerabilities"])
            if phase == "post_remediation"
            else set(expected["expected_vulnerabilities"]).issubset(
                observed_vulnerabilities
            )
        )
        risk_levels = sorted(
            {
                DeterministicRiskEngine()
                .assess(path.attack_type, path.steps or [], path.details or {})
                .severity
                for path in paths
            }
        )
        risk_match = self._risk_matches_expectation(
            expected["expected_risk"],
            risk_levels,
        )
        passed = count_passed and resources_match and vulnerability_match and risk_match
        actual = {
            "resource_count": len(nodes),
            "observed_resource_names": sorted(names),
            "attack_path_count": path_count,
            "sensitive_bucket_path_count": len(observed_bucket_paths),
            "vulnerabilities": observed_vulnerabilities,
            "risk_levels": risk_levels,
            "attack_path_count_matches_expectation": count_passed,
            "resources_match_expectation": resources_match,
            "vulnerabilities_match_expectation": vulnerability_match,
            "risk_matches_expectation": risk_match,
            "passed": passed,
        }
        actual_results = dict(run.actual_results or {})
        assertion = {
            "phase": phase,
            "expected": expected,
            "actual": actual,
            "passed": passed,
        }
        actual_results[phase] = assertion
        await self._scenarios.set_actual_results(run, actual_results)
        await self._session.commit()
        return assertion

    async def active_manifest(self, workspace_id: UUID | str) -> dict[str, Any] | None:
        run = await self._scenarios.active_for_workspace(UUID(str(workspace_id)))
        return run.resource_manifest if run else None

    async def _ensure_workspace(self, workspace_id: UUID, owner_id: str):
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError("Workspace not found")
        if str(workspace.owner_id) != str(owner_id):
            raise WorkspaceAccessDeniedError("You do not own this workspace")
        return workspace

    async def _has_existing_workspace_data(self, workspace_id: UUID) -> bool:
        for model in (
            CloudDiscoveredResourceModel,
            GraphNodeModel,
            GraphEdgeModel,
            AttackPathModel,
            FindingModel,
            IamAgentRunModel,
            DiscoveryRunModel,
        ):
            result = await self._session.execute(
                select(model.workspace_id).where(model.workspace_id == workspace_id).limit(1)
            )
            if result.first() is not None:
                return True
        return False

    async def _remediation_policies(self, workspace_id: UUID) -> list[dict[str, Any]]:
        result = await self._session.execute(
            select(IamAgentRunModel.attempts).where(
                IamAgentRunModel.workspace_id == workspace_id
            )
        )
        policies: list[dict[str, Any]] = []
        for attempts in result.scalars().all():
            for attempt in attempts or []:
                rollback = attempt.get("rollback") or {}
                if rollback.get("operation") not in {
                    "delete_user_policy",
                    "delete_role_policy",
                }:
                    continue
                policies.append(
                    {
                        "principal_type": (
                            "user"
                            if rollback.get("principal_parameter") == "UserName"
                            else "role"
                        ),
                        "principal_name": rollback.get("principal_name", ""),
                        "policy_name": rollback.get("policy_name", ""),
                        "rollback": rollback,
                    }
                )
        return policies

    def _localstack_clients(self) -> dict[str, Any]:
        LocalStackIamExecutor(None, self._endpoint_url).check_ready()
        session = boto3.Session(
            aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY,
            region_name=self._settings.AWS_REGION,
        )
        return {
            name: session.client(
                name,
                endpoint_url=self._endpoint_url,
                region_name=self._settings.AWS_REGION,
            )
            for name in ("iam", "s3", "sts")
        }

    @staticmethod
    def _manifest_for(scenario, suffix: str, run_id: UUID) -> dict[str, Any]:
        prefix = f"sentinel-{scenario.scenario_id[:12]}-{suffix}"
        users_count, roles_count = {
            "secure": (1, 1),
            "direct_s3": (1, 0),
            "explicit_deny": (1, 0),
            "direct_role": (1, 1),
            "role_chain": (1, 3),
            "long_role_chain": (1, 5),
            "role_cycle": (1, 2),
            "shared_role": (2, 1),
            "multiple_paths": (2, 2),
        }[scenario.topology]
        users = [f"{prefix}-u{index + 1}" for index in range(users_count)]
        roles = [f"{prefix}-r{index + 1}" for index in range(roles_count)]
        bucket = f"{prefix}-data"
        object_key = "confidential/report.txt"
        policies: list[dict[str, str]] = []
        if scenario.topology in {"direct_s3", "explicit_deny"}:
            policies.append(
                {
                    "principal_type": "user",
                    "principal_name": users[0],
                    "policy_name": f"Sentinel-{run_id.hex[:12]}-UserAccess",
                }
            )
        data_roles = (
            roles[-1:]
            if scenario.topology in {"role_chain", "long_role_chain", "role_cycle"}
            else roles
            if scenario.topology in {"direct_role", "shared_role", "multiple_paths"}
            else []
        )
        for role_name in data_roles:
            policies.append({"principal_type": "role", "principal_name": role_name, "policy_name": f"Sentinel-{run_id.hex[:12]}-{role_name[-2:]}-Data"})
        assume_principals = (
            [("user", users[0]), *[("role", name) for name in roles[:-1]]]
            if scenario.topology in {"role_chain", "long_role_chain"}
            else [
                ("user", users[0]),
                ("role", roles[0]),
                ("role", roles[1]),
            ]
            if scenario.topology == "role_cycle"
            else [("user", name) for name in users]
            if scenario.topology in {"direct_role", "shared_role", "multiple_paths"}
            else []
        )
        for principal_type, principal_name in assume_principals:
            policies.append(
                {
                    "principal_type": principal_type,
                    "principal_name": principal_name,
                    "policy_name": f"Sentinel-{run_id.hex[:12]}-{principal_name[-2:]}-Assume",
                }
            )
        resource_keys = [
            *({"resource_type": "iam_user", "resource_id": name} for name in users),
            *({"resource_type": "iam_role", "resource_id": name} for name in roles),
            {"resource_type": "s3_bucket", "resource_id": bucket},
        ]
        return {
            "scenario_id": scenario.scenario_id,
            "run_id": str(run_id),
            "users": users,
            "roles": roles,
            "bucket_name": bucket,
            "object_keys": [object_key],
            "inline_policies": policies,
            "resource_keys": resource_keys,
            "tag_workspace_id": suffix,
        }

    @staticmethod
    def _expected_results(scenario, manifest: dict[str, Any]) -> dict[str, Any]:
        value = scenario.to_dict()
        value["expected_min_paths"] = scenario.expected_min_paths
        value["expected_max_paths"] = scenario.expected_max_paths
        value["expected_bucket_name"] = manifest["bucket_name"]
        return value

    @staticmethod
    def _seed(clients, topology: str, manifest: dict[str, Any], workspace_id: str, run_id: str) -> None:
        iam, s3 = clients["iam"], clients["s3"]
        user_arns: list[str] = []
        role_arns: list[str] = []
        bucket = manifest["bucket_name"]
        try:
            s3.create_bucket(Bucket=bucket)
        except s3.exceptions.BucketAlreadyOwnedByYou:
            pass
        s3.put_bucket_tagging(
            Bucket=bucket,
            Tagging={
                "TagSet": [
                    {"Key": "sentinel-workspace-id", "Value": workspace_id},
                    {"Key": "sentinel-scenario-run-id", "Value": run_id},
                ]
            },
        )
        s3.put_object(
            Bucket=bucket,
            Key=manifest["object_keys"][0],
            Body=b"LocalStack-only SENTINEL scenario data",
        )
        for username in manifest["users"]:
            user = iam.create_user(
                UserName=username,
                Tags=[
                    {"Key": "sentinel-workspace-id", "Value": workspace_id},
                    {"Key": "sentinel-scenario-run-id", "Value": run_id},
                ],
            )["User"]
            user_arns.append(user["Arn"])

        topology_trusts: list[list[str]] = []
        if topology == "direct_role":
            topology_trusts = [[user_arns[0]]]
        elif topology in {"role_chain", "long_role_chain"}:
            topology_trusts = [[user_arns[0]], *[[] for _ in manifest["roles"][1:]]]
        elif topology == "role_cycle":
            account_id = clients["sts"].get_caller_identity()["Account"]
            role_arns_by_name = {
                name: f"arn:aws:iam::{account_id}:role/{name}"
                for name in manifest["roles"]
            }
            topology_trusts = [
                [user_arns[0]],
                [role_arns_by_name[manifest["roles"][0]]],
            ]
        elif topology == "shared_role":
            topology_trusts = [user_arns]
        elif topology == "multiple_paths":
            topology_trusts = [[user_arns[index]] for index in range(len(manifest["roles"]))]
        elif topology == "secure":
            topology_trusts = [[user_arns[0]]]

        for index, role_name in enumerate(manifest["roles"]):
            if topology in {"role_chain", "long_role_chain"} and index > 0:
                topology_trusts[index] = [role_arns[index - 1]]
            trust = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": principals[0] if len(principals) == 1 else principals},
                        "Action": "sts:AssumeRole",
                    }
                    for principals in [topology_trusts[index]]
                    if principals
                ],
            }
            created = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust),
                Tags=[
                    {"Key": "sentinel-workspace-id", "Value": workspace_id},
                    {"Key": "sentinel-scenario-run-id", "Value": run_id},
                ],
            )["Role"]
            role_arns.append(created["Arn"])

        if topology == "role_cycle":
            iam.update_assume_role_policy(
                RoleName=manifest["roles"][0],
                PolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": {
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": [user_arns[0], role_arns[1]],
                            },
                            "Action": "sts:AssumeRole",
                        },
                    }
                ),
            )

        policies_by_key = {
            (item["principal_type"], item["principal_name"]): item["policy_name"]
            for item in manifest["inline_policies"]
        }
        if topology in {"direct_s3", "explicit_deny"}:
            statement = {
                "Effect": "Allow",
                "Action": "s3:GetObject" if topology == "explicit_deny" else ["s3:GetObject", "s3:PutObject"],
                "Resource": f"arn:aws:s3:::{bucket}/*",
            }
            statements = [statement]
            if topology == "explicit_deny":
                statements.append(
                    {
                        "Effect": "Deny",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket}/*",
                    }
                )
            iam.put_user_policy(
                UserName=manifest["users"][0],
                PolicyName=policies_by_key[("user", manifest["users"][0])],
                PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}),
            )

        if topology == "direct_role":
            ScenarioService._allow_assume_role(
                iam, "user", manifest["users"][0], policies_by_key[("user", manifest["users"][0])], [role_arns[0]]
            )
        elif topology in {"role_chain", "long_role_chain"}:
            ScenarioService._allow_assume_role(
                iam, "user", manifest["users"][0], policies_by_key[("user", manifest["users"][0])], [role_arns[0]]
            )
            for index in range(len(role_arns) - 1):
                ScenarioService._allow_assume_role(
                    iam,
                    "role",
                    manifest["roles"][index],
                    policies_by_key[("role", manifest["roles"][index])],
                    [role_arns[index + 1]],
                )
        elif topology == "role_cycle":
            ScenarioService._allow_assume_role(
                iam, "user", manifest["users"][0], policies_by_key[("user", manifest["users"][0])], [role_arns[0]]
            )
            for index in range(len(role_arns)):
                next_role = role_arns[(index + 1) % len(role_arns)]
                ScenarioService._allow_assume_role(
                    iam,
                    "role",
                    manifest["roles"][index],
                    policies_by_key[("role", manifest["roles"][index])],
                    [next_role],
                )
        elif topology == "shared_role":
            for username in manifest["users"]:
                ScenarioService._allow_assume_role(
                    iam, "user", username, policies_by_key[("user", username)], [role_arns[0]]
                )
        elif topology == "multiple_paths":
            for index, username in enumerate(manifest["users"]):
                ScenarioService._allow_assume_role(
                    iam, "user", username, policies_by_key[("user", username)], [role_arns[index]]
                )

        resource_roles = (
            [role_arns[-1]]
            if topology in {"role_chain", "long_role_chain", "role_cycle"}
            else role_arns
            if topology in {"direct_role", "shared_role", "multiple_paths"}
            else []
        )
        for role_arn, role_name in zip(role_arns, manifest["roles"]):
            if role_arn not in resource_roles:
                continue
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policies_by_key[("role", role_name)],
                PolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": {
                            "Effect": "Allow",
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{bucket}/*",
                        },
                    }
                ),
            )

    @staticmethod
    def _allow_assume_role(
        iam, principal_type: str, principal_name: str, policy_name: str, role_arns: list[str]
    ) -> None:
        operation = "put_user_policy" if principal_type == "user" else "put_role_policy"
        parameter = "UserName" if principal_type == "user" else "RoleName"
        getattr(iam, operation)(
            **{parameter: principal_name},
            PolicyName=policy_name,
            PolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": {
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Resource": role_arns,
                    },
                }
            ),
        )

    @staticmethod
    def _delete_fixture_resources(clients, manifest: dict[str, Any]) -> None:
        iam, s3 = clients["iam"], clients["s3"]
        expected_prefix = f"sentinel-{manifest.get('scenario_id', '')[:12]}-"
        for policy in manifest.get("inline_policies", []):
            principal_name = policy.get("principal_name", "")
            if not principal_name.startswith(expected_prefix):
                raise ValueError("Scenario manifest contains a principal outside its ownership prefix")
            principal_type = policy["principal_type"]
            operation = {
                "user": "delete_user_policy",
                "role": "delete_role_policy",
            }.get(principal_type)
            parameter = "UserName" if principal_type == "user" else "RoleName"
            if operation is None:
                raise ValueError(f"Unsupported fixture principal type: {principal_type}")
            try:
                getattr(iam, operation)(
                    **{parameter: principal_name},
                    PolicyName=policy["policy_name"],
                )
            except iam.exceptions.NoSuchEntityException:
                pass

        for role_name in manifest.get("roles", []):
            if not role_name.startswith(expected_prefix):
                raise ValueError("Scenario manifest contains a role outside its ownership prefix")
            try:
                iam.delete_role(RoleName=role_name)
            except iam.exceptions.NoSuchEntityException:
                pass
        for user_name in manifest.get("users", []):
            if not user_name.startswith(expected_prefix):
                raise ValueError("Scenario manifest contains a user outside its ownership prefix")
            try:
                iam.delete_user(UserName=user_name)
            except iam.exceptions.NoSuchEntityException:
                pass

        bucket = manifest.get("bucket_name", "")
        if bucket:
            if not bucket.startswith(expected_prefix):
                raise ValueError("Scenario manifest contains a bucket outside its ownership prefix")
            for object_key in manifest.get("object_keys", []):
                try:
                    s3.delete_object(Bucket=bucket, Key=object_key)
                except s3.exceptions.NoSuchBucket:
                    break
            try:
                s3.delete_bucket(Bucket=bucket)
            except s3.exceptions.NoSuchBucket:
                pass

    @staticmethod
    def _observed_vulnerabilities(paths: list) -> list[str]:
        vulnerabilities: set[str] = set()
        entries: set[str] = set()
        path_count = len(paths)
        for path in paths:
            steps = path.steps or []
            if path.attack_type == "s3_access":
                vulnerabilities.add("s3_access")
            if any(step.get("node_type") == "iam_role" for step in steps):
                vulnerabilities.add("assume_role_escalation")
            if len(steps) >= 4:
                vulnerabilities.add("multi_hop_assume_role")
            if steps and steps[0].get("node_type") == "iam_user":
                entries.add(str(steps[0].get("external_id")))
            evidence = (path.details or {}).get("edge_evidence", [])
            if any(
                action in {"s3:PutObject", "s3:DeleteObject"}
                for item in evidence
                if isinstance(item, dict)
                for action in (item.get("details") or {}).get("actions", [])
            ):
                vulnerabilities.add("excessive_s3_permissions")
        if len(entries) > 1:
            vulnerabilities.add("multiple_entry_points")
        if path_count > 1:
            vulnerabilities.add("multiple_attack_paths")
        return sorted(vulnerabilities)

    @staticmethod
    def _risk_matches_expectation(expected: str, actual_levels: list[str]) -> bool:
        if expected == "none":
            return not actual_levels
        expected_levels = {level.strip() for level in expected.split("or")}
        return bool(expected_levels.intersection(actual_levels))
