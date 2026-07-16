"""Service for enumerating AWS resources through LocalStack."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import boto3

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
    ) -> None:
        self._discovery_runs = discovery_repository
        self._workspaces = workspace_repository
        self._cloud_resources = cloud_resource_repository
        self._client_factory = client_factory or self._default_client_factory

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
            discovered_resources.extend(self._discover_iam_policies(clients))
            discovered_resources.extend(self._discover_s3_buckets(clients))
            discovered_resources.extend(self._discover_ec2_instances(clients))
            discovered_resources.extend(self._discover_vpcs(clients))
            discovered_resources.extend(self._discover_security_groups(clients))
        except Exception as exc:  # pragma: no cover - exercised by worker failure path
            await self._discovery_runs.update_status(
                discovery_run_id,
                status="failed",
                summary=f"Discovery failed: {exc}",
            )
            raise

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

        await self._discovery_runs.update_status(
            discovery_run_id,
            status="completed",
            summary=f"Discovered {len(discovered_resources)} AWS resource(s)",
            resource_count=len(discovered_resources),
            discovered_resources=[{"type": item["resource_type"], "name": item["name"]} for item in discovered_resources],
            completed_at=datetime.now(timezone.utc),
        )
        return len(discovered_resources)

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
        }

    def _discover_iam_users(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "iam_user",
            clients["iam"].list_users().get("Users", []),
            lambda user: {
                "resource_id": user.get("UserName") or user.get("UserId") or "unknown",
                "name": user.get("UserName") or user.get("UserId") or "unknown",
                "arn": user.get("Arn"),
                "details": {"user_id": user.get("UserId")},
            },
        )

    def _discover_iam_roles(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "iam_role",
            clients["iam"].list_roles().get("Roles", []),
            lambda role: {
                "resource_id": role.get("RoleName") or role.get("RoleId") or "unknown",
                "name": role.get("RoleName") or role.get("RoleId") or "unknown",
                "arn": role.get("Arn"),
                "details": {"role_id": role.get("RoleId")},
            },
        )

    def _discover_iam_groups(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "iam_group",
            clients["iam"].list_groups().get("Groups", []),
            lambda group: {
                "resource_id": group.get("GroupName") or group.get("GroupId") or "unknown",
                "name": group.get("GroupName") or group.get("GroupId") or "unknown",
                "arn": group.get("Arn"),
                "details": {"group_id": group.get("GroupId")},
            },
        )

    def _discover_iam_policies(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "iam_policy",
            clients["iam"].list_policies(Scope="Local").get("Policies", []),
            lambda policy: {
                "resource_id": policy.get("PolicyName") or policy.get("PolicyId") or "unknown",
                "name": policy.get("PolicyName") or policy.get("PolicyId") or "unknown",
                "arn": policy.get("Arn"),
                "details": {"policy_id": policy.get("PolicyId")},
            },
        )

    def _discover_s3_buckets(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "s3_bucket",
            clients["s3"].list_buckets().get("Buckets", []),
            lambda bucket: {
                "resource_id": bucket.get("Name") or "unknown",
                "name": bucket.get("Name") or "unknown",
                "arn": None,
                "details": {"creation_date": str(bucket.get("CreationDate", ""))},
            },
        )

    def _discover_ec2_instances(self, clients: dict[str, Any]) -> list[dict[str, Any]]:
        return self._normalize_resources(
            "ec2_instance",
            clients["ec2"].describe_instances().get("Reservations", []),
            lambda reservation: {
                "resource_id": reservation.get("Instances", [{}])[0].get("InstanceId") or "unknown",
                "name": reservation.get("Instances", [{}])[0].get("InstanceId") or "unknown",
                "arn": None,
                "details": {"instance_state": str(reservation.get("Instances", [{}])[0].get("State", {}).get("Name", ""))},
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
                "details": {"cidr_block": vpc.get("CidrBlock")},
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
                "details": {"description": group.get("Description")},
            },
        )

    def _normalize_resources(self, resource_type: str, items: list[dict[str, Any]], mapper: Callable[[dict[str, Any]], dict[str, Any]]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for item in items:
            normalized = mapper(item)
            resources.append({"resource_type": resource_type, **normalized})
        return resources
