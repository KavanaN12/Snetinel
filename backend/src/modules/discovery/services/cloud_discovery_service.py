"""Service for enumerating AWS resources through LocalStack."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from src.modules.discovery.domain.entities import DiscoveryRun, DiscoveredCloudResource
from src.modules.discovery.repositories.cloud_resource_repository import CloudResourceRepository
from src.modules.discovery.repositories.discovery_repository import DiscoveryRepository
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository
from src.shared.config.settings import get_settings

settings = get_settings()


class CloudDiscoveryService:
    def __init__(
        self,
        discovery_repository: DiscoveryRepository,
        workspace_repository: WorkspaceRepository,
        cloud_resource_repository: CloudResourceRepository,
        client_factory: Callable[[], dict[str, Any]] | None = None,
        scenario_run_repository: Any | None = None,
    ) -> None:
        self._discovery_runs = discovery_repository
        self._workspaces = workspace_repository
        self._cloud_resources = cloud_resource_repository
        self._client_factory = client_factory or self._default_client_factory
        self._scenario_runs = scenario_run_repository

    async def process_discovery_job(self, *, workspace_id: UUID | str, discovery_run_id: UUID | str) -> int:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            return 0

        await self._discovery_runs.update_status(discovery_run_id, status="running", summary="Enumerating AWS resources")

        discovered_resources: list[dict[str, Any]] = []
        try:
            clients = self._client_factory()
            discovered_resources.extend(self._discover_iam_users(clients))
            discovered_resources.extend(self._discover_iam_roles(clients))
            discovered_resources.extend(self._discover_iam_groups(clients))
            discovered_resources.extend(self._discover_iam_policies(clients, discovered_resources))
            discovered_resources.extend(self._discover_s3_buckets(clients))
            discovered_resources.extend(self._discover_ec2_instances(clients))
            discovered_resources.extend(self._discover_vpcs(clients))
            discovered_resources.extend(self._discover_security_groups(clients))
            discovered_resources.extend(self._discover_kms_keys(clients))
            discovered_resources.extend(self._discover_lambda_functions(clients))
        except Exception as exc:  # pragma: no cover - exercised by worker failure path
            await self._discovery_runs.update_status(
                discovery_run_id,
                status="failed",
                summary=f"Discovery failed: {exc}",
            )
            raise

        if self._scenario_runs is not None:
            scenario_run = await self._scenario_runs.active_for_workspace(workspace.id)
            if scenario_run is not None:
                discovered_resources = self._filter_scenario_resources(
                    discovered_resources,
                    scenario_run.resource_manifest,
                )

        for resource in discovered_resources:
            await self._cloud_resources.create_or_update(
                workspace_id=workspace.id,
                discovery_run_id=discovery_run_id,
                resource_type=resource["resource_type"],
                resource_id=resource["resource_id"],
                name=resource["name"],
                arn=resource.get("arn"),
                details=resource.get("details", {}),
            )

        await self._cloud_resources.retain_snapshot(
            workspace_id=workspace.id,
            resource_keys=[
                (resource["resource_type"], resource["resource_id"])
                for resource in discovered_resources
            ],
        )

        await self._discovery_runs.update_status(
            discovery_run_id,
            status="completed",
            summary=f"Discovered {len(discovered_resources)} AWS resource(s)",
            resource_count=len(discovered_resources),
            discovered_resources=[{"type": item["resource_type"], "name": item["name"]} for item in discovered_resources],
            completed_at=datetime.now(timezone.utc),
        )
        return len(discovered_resources)

    @staticmethod
    def _filter_scenario_resources(
        discovered_resources: list[dict[str, Any]],
        manifest: dict[str, Any],
    ) -> list[dict[str, Any]]:
        allowed_resources = {
            (item.get("resource_type"), item.get("resource_id"))
            for item in manifest.get("resource_keys", [])
            if isinstance(item, dict)
        }
        return [
            resource
            for resource in discovered_resources
            if (resource["resource_type"], resource["resource_id"]) in allowed_resources
        ]

    def _default_client_factory(self) -> dict[str, Any]:
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        return {
            "iam": session.client("iam", endpoint_url=settings.AWS_ENDPOINT_URL, region_name=settings.AWS_REGION),
            "s3": session.client("s3", endpoint_url=settings.AWS_ENDPOINT_URL, region_name=settings.AWS_REGION),
            "ec2": session.client("ec2", endpoint_url=settings.AWS_ENDPOINT_URL, region_name=settings.AWS_REGION),
            "kms": session.client("kms", endpoint_url=settings.AWS_ENDPOINT_URL, region_name=settings.AWS_REGION),
            "lambda": session.client("lambda", endpoint_url=settings.AWS_ENDPOINT_URL, region_name=settings.AWS_REGION),
            "sts": session.client("sts", endpoint_url=settings.AWS_ENDPOINT_URL, region_name=settings.AWS_REGION),
        }

    def _discover_iam_users(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        iam = clients["iam"]
        resources = []
        for user in self._list_iam_pages(iam, "list_users", "Users"):
            user_name = user.get("UserName") or user.get("UserId") or "unknown"
            attached = self._list_iam_pages(
                iam, "list_attached_user_policies", "AttachedPolicies", UserName=user_name
            )
            group_names = [
                group.get("GroupName")
                for group in self._list_iam_pages(
                    iam, "list_groups_for_user", "Groups", UserName=user_name
                )
                if group.get("GroupName")
            ]
            resources.append(
                {
                    "resource_type": "iam_user",
                    "resource_id": user_name,
                    "name": user_name,
                    "arn": user.get("Arn"),
                    "details": {
                        "user_id": user.get("UserId"),
                        "arn": user.get("Arn"),
                        "attached_policy_arns": sorted(
                            item["PolicyArn"] for item in attached if item.get("PolicyArn")
                        ),
                        "inline_policies": self._fetch_inline_policies(
                            iam, "list_user_policies", "get_user_policy", UserName=user_name
                        ),
                        "group_names": sorted(group_names),
                        "permissions_boundary_arn": (
                            user.get("PermissionsBoundary", {}).get("PermissionsBoundaryArn")
                        ),
                    },
                }
            )
        return resources

    def _discover_iam_roles(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        iam = clients["iam"]
        resources = []
        for role in self._list_iam_pages(iam, "list_roles", "Roles"):
            role_name = role.get("RoleName") or role.get("RoleId") or "unknown"
            attached = self._list_iam_pages(
                iam, "list_attached_role_policies", "AttachedPolicies", RoleName=role_name
            )
            resources.append(
                {
                    "resource_type": "iam_role",
                    "resource_id": role_name,
                    "name": role_name,
                    "arn": role.get("Arn"),
                    "details": {
                        "role_id": role.get("RoleId"),
                        "arn": role.get("Arn"),
                        "trust_policy": role.get("AssumeRolePolicyDocument"),
                        "trusted_principals": self._extract_trusted_principals(
                            role.get("AssumeRolePolicyDocument")
                        ),
                        "attached_policy_arns": sorted(
                            item["PolicyArn"] for item in attached if item.get("PolicyArn")
                        ),
                        "inline_policies": self._fetch_inline_policies(
                            iam, "list_role_policies", "get_role_policy", RoleName=role_name
                        ),
                        "permissions_boundary_arn": (
                            role.get("PermissionsBoundary", {}).get("PermissionsBoundaryArn")
                        ),
                    },
                }
            )
        return resources

    def _discover_iam_groups(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        iam = clients["iam"]
        resources = []
        for group in self._list_iam_pages(iam, "list_groups", "Groups"):
            group_name = group.get("GroupName") or group.get("GroupId") or "unknown"
            attached = self._list_iam_pages(
                iam, "list_attached_group_policies", "AttachedPolicies", GroupName=group_name
            )
            members = self._list_iam_pages(
                iam, "get_group", "Users", GroupName=group_name
            )
            resources.append(
                {
                    "resource_type": "iam_group",
                    "resource_id": group_name,
                    "name": group_name,
                    "arn": group.get("Arn"),
                    "details": {
                        "group_id": group.get("GroupId"),
                        "member_user_names": sorted(
                            user["UserName"] for user in members if user.get("UserName")
                        ),
                        "attached_policy_arns": sorted(
                            item["PolicyArn"] for item in attached if item.get("PolicyArn")
                        ),
                        "inline_policies": self._fetch_inline_policies(
                            iam, "list_group_policies", "get_group_policy", GroupName=group_name
                        ),
                    },
                }
            )
        return resources

    def _discover_iam_policies(
        self,
        clients: dict[str, Any],
        identity_resources: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        iam = clients["iam"]
        policies = self._list_iam_pages(iam, "list_policies", "Policies", Scope="Local")
        known_arns = {item.get("Arn") for item in policies}
        required_arns = {
            str(policy_arn)
            for identity in identity_resources or []
            for policy_arn in (
                (identity.get("details") or {}).get("attached_policy_arns", [])
                + [
                    (identity.get("details") or {}).get("permissions_boundary_arn")
                ]
            )
            if policy_arn
        }
        for policy_arn in sorted(required_arns - known_arns):
            attached_policy = iam.get_policy(PolicyArn=policy_arn).get("Policy")
            if attached_policy:
                policies.append(attached_policy)

        resources = []
        for policy in policies:
            arn = policy.get("Arn")
            document = policy.get("PolicyDocument")
            if arn and not isinstance(document, dict):
                policy_details = policy
                if not policy_details.get("DefaultVersionId"):
                    policy_details = iam.get_policy(PolicyArn=arn).get("Policy", {})
                version_id = policy_details.get("DefaultVersionId") or policy.get("DefaultVersionId")
                if version_id:
                    document = iam.get_policy_version(
                        PolicyArn=arn,
                        VersionId=version_id,
                    ).get("PolicyVersion", {}).get("Document")
            policy_name = policy.get("PolicyName") or policy.get("PolicyId") or "unknown"
            resources.append(
                {
                    "resource_type": "iam_policy",
                    "resource_id": arn or policy_name,
                    "name": policy_name,
                    "arn": arn,
                    "details": {
                        "policy_id": policy.get("PolicyId"),
                        "policy_arn": arn,
                        "document": document,
                        "actions": self._extract_policy_actions(document),
                        "default_version_id": policy.get("DefaultVersionId"),
                        "attachment_count": policy.get("AttachmentCount", 0),
                    },
                }
            )
        return resources

    @staticmethod
    def _list_iam_pages(
        client: Any,
        operation: str,
        result_key: str,
        **parameters: Any,
    ) -> list[dict[str, Any]]:
        method = getattr(client, operation)
        items: list[dict[str, Any]] = []
        request = dict(parameters)
        previous_marker = None
        while True:
            response = method(**request)
            items.extend(response.get(result_key, []))
            marker = response.get("Marker")
            if not response.get("IsTruncated") or not marker or marker == previous_marker:
                break
            previous_marker = marker
            request["Marker"] = marker
        return items

    @classmethod
    def _fetch_inline_policies(
        cls,
        client: Any,
        list_operation: str,
        get_operation: str,
        **identity: str,
    ) -> list[dict[str, Any]]:
        policy_names = cls._list_iam_pages(client, list_operation, "PolicyNames", **identity)
        inline_policies = []
        for policy_name in policy_names:
            policy_document = getattr(client, get_operation)(
                **identity,
                PolicyName=policy_name,
            ).get("PolicyDocument")
            inline_policies.append(
                {"name": policy_name, "document": policy_document}
            )
        return inline_policies

    def _discover_s3_buckets(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        account_id = clients.get("sts", {}).get_caller_identity().get("Account") if clients.get("sts") else None
        resources = []
        for bucket in clients["s3"].list_buckets().get("Buckets", []):
            bucket_name = bucket.get("Name")
            if not bucket_name:
                continue
            bucket_policy = None
            try:
                bucket_policy = clients["s3"].get_bucket_policy(Bucket=bucket_name).get("Policy")
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") != "NoSuchBucketPolicy":
                    raise
            resources.append(
                {
                    "resource_type": "s3_bucket",
                    "resource_id": bucket_name,
                    "name": bucket_name,
                    "arn": f"arn:aws:s3:::{bucket_name}",
                    "details": {
                        "creation_date": str(bucket.get("CreationDate", "")),
                        "account_id": account_id,
                        "resource_policy": bucket_policy,
                    },
                }
            )
        return resources

    def _discover_ec2_instances(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        response = self._list_token_pages(clients["ec2"], "describe_instances", "Reservations")
        instances = [
            instance
            for reservation in response
            for instance in reservation.get("Instances", [])
        ]
        account_id = clients.get("sts", {}).get_caller_identity().get("Account") if clients.get("sts") else None
        return self._normalize_resources(
            "ec2_instance",
            instances,
            lambda instance: {
                "resource_id": instance.get("InstanceId") or "unknown",
                "name": instance.get("InstanceId") or "unknown",
                "arn": (
                    f"arn:aws:ec2:{settings.AWS_REGION}:{account_id}:instance/{instance.get('InstanceId')}"
                    if account_id and instance.get("InstanceId")
                    else None
                ),
                "details": {
                    "instance_state": str(instance.get("State", {}).get("Name", "")),
                    "vpc_id": instance.get("VpcId"),
                    "subnet_id": instance.get("SubnetId"),
                    "security_group_ids": sorted(
                        group.get("GroupId")
                        for group in instance.get("SecurityGroups", [])
                        if group.get("GroupId")
                    ),
                    "iam_instance_profile_arn": instance.get("IamInstanceProfile", {}).get("Arn"),
                },
            },
        )

    def _discover_vpcs(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "vpc",
            clients["ec2"].describe_vpcs().get("Vpcs", []),
            lambda vpc: {
                "resource_id": vpc.get("VpcId") or "unknown",
                "name": vpc.get("VpcId") or "unknown",
                "arn": None,
                "details": {
                    "cidr_block": vpc.get("CidrBlock"),
                    "is_default": vpc.get("IsDefault", False),
                },
            },
        )

    def _discover_security_groups(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "security_group",
            clients["ec2"].describe_security_groups().get("SecurityGroups", []),
            lambda group: {
                "resource_id": group.get("GroupId") or "unknown",
                "name": group.get("GroupName") or group.get("GroupId") or "unknown",
                "arn": None,
                "details": {
                    "description": group.get("Description"),
                    "vpc_id": group.get("VpcId"),
                    "ingress_rules": group.get("IpPermissions", []),
                    "egress_rules": group.get("IpPermissionsEgress", []),
                },
            },
        )

    def _discover_kms_keys(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        keys = self._list_token_pages(clients["kms"], "list_keys", "Keys")
        resources = []
        for key in keys:
            key_id = key.get("KeyId")
            if not key_id:
                continue
            metadata = clients["kms"].describe_key(KeyId=key_id).get("KeyMetadata", {})
            policy_response = clients["kms"].get_key_policy(
                KeyId=key_id,
                PolicyName="default",
            )
            resources.append(
                {
                    "resource_type": "kms_key",
                    "resource_id": key_id,
                    "name": key_id,
                    "arn": metadata.get("Arn"),
                    "details": {
                        "key_id": key_id,
                        "key_manager": metadata.get("KeyManager"),
                        "key_state": metadata.get("KeyState"),
                        "key_usage": metadata.get("KeyUsage"),
                        "key_spec": metadata.get("KeySpec"),
                        "key_policy": policy_response.get("Policy"),
                        "enabled": metadata.get("Enabled"),
                    },
                }
            )
        return resources

    def _discover_lambda_functions(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        functions = self._list_token_pages(clients["lambda"], "list_functions", "Functions")
        resources = []
        for function in functions:
            function_arn = function.get("FunctionArn")
            function_name = function.get("FunctionName") or function_arn or "unknown"
            resource_policy = None
            if function_arn:
                try:
                    resource_policy = clients["lambda"].get_policy(
                        FunctionName=function_arn
                    ).get("Policy")
                except clients["lambda"].exceptions.ResourceNotFoundException:
                    resource_policy = None
            resources.append(
                {
                    "resource_type": "lambda_function",
                    "resource_id": function_name,
                    "name": function_name,
                    "arn": function_arn,
                    "details": {
                        "runtime": function.get("Runtime"),
                        "handler": function.get("Handler"),
                        "role_arn": function.get("Role"),
                        "last_modified": function.get("LastModified"),
                        "resource_policy": resource_policy,
                    },
                }
            )
        return resources

    @staticmethod
    def _list_token_pages(
        client: Any,
        operation: str,
        result_key: str,
        **parameters: Any,
    ) -> list[dict[str, Any]]:
        method = getattr(client, operation)
        items: list[dict[str, Any]] = []
        request = dict(parameters)
        previous_token = None
        while True:
            response = method(**request)
            items.extend(response.get(result_key, []))
            token = response.get("NextToken") or response.get("NextMarker")
            if not token or token == previous_token:
                break
            previous_token = token
            if "NextMarker" in response:
                request["Marker"] = token
            else:
                request["NextToken"] = token
        return items

    def _normalize_resources(self, resource_type: str, items: list[dict[str, Any]], mapper: Callable[[dict[str, Any]], dict[str, Any]]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for item in items:
            normalized = mapper(item)
            resources.append({"resource_type": resource_type, **normalized})
        return resources

    @staticmethod
    def _extract_trusted_principals(policy_document: Any) -> list[str]:
        if not isinstance(policy_document, dict):
            return []
        statement = policy_document.get("Statement")
        if not isinstance(statement, list):
            statement = [statement] if statement else []

        principals: list[str] = []
        for item in statement:
            if not isinstance(item, dict):
                continue
            principal = item.get("Principal")
            if isinstance(principal, dict):
                for key, value in principal.items():
                    if isinstance(value, list):
                        principals.extend(str(v) for v in value)
                    elif value is not None:
                        principals.append(str(value))
            elif principal is not None:
                principals.append(str(principal))
        return sorted(set(principals))

    @staticmethod
    def _extract_policy_actions(policy_document: Any) -> list[str]:
        if not isinstance(policy_document, dict):
            return []
        statement = policy_document.get("Statement")
        if not isinstance(statement, list):
            statement = [statement] if statement else []

        actions: list[str] = []
        for item in statement:
            if not isinstance(item, dict):
                continue
            action = item.get("Action")
            if isinstance(action, list):
                actions.extend(str(value) for value in action)
            elif action is not None:
                actions.append(str(action))
        return sorted(set(actions))
