"""Abstract repository contract for discovered cloud resources."""

from typing import Protocol
from uuid import UUID

from src.modules.discovery.domain.entities import DiscoveredCloudResource


class CloudResourceRepository(Protocol):
    async def create_or_update(
        self,
        *,
        workspace_id: UUID | str,
        discovery_run_id: UUID | str,
        resource_type: str,
        resource_id: str,
        name: str,
        arn: str | None,
        details: dict[str, object],
    ) -> DiscoveredCloudResource: ...

    async def list_by_workspace(self, workspace_id: UUID | str) -> list[DiscoveredCloudResource]: ...

    async def get_by_id(self, resource_id: UUID | str) -> DiscoveredCloudResource | None: ...
