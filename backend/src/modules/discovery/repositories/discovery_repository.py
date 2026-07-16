"""Abstract discovery repository contract."""

from typing import Protocol
from uuid import UUID

from src.modules.discovery.domain.entities import DiscoveryRun


class DiscoveryRepository(Protocol):
    async def create(
        self,
        *,
        workspace_id: UUID | str,
        status: str,
        summary: str,
        resource_count: int,
        discovered_resources: list[dict[str, str]],
        started_at,
        completed_at,
    ) -> DiscoveryRun: ...

    async def list_by_workspace(self, workspace_id: UUID | str) -> list[DiscoveryRun]: ...

    async def get_by_id(self, discovery_run_id: UUID | str) -> DiscoveryRun | None: ...
