"""Discovery service layer."""

from datetime import datetime, timezone
from uuid import UUID

from src.modules.discovery.domain.entities import DiscoveryRun, DiscoveredCloudResource
from src.modules.discovery.domain.exceptions import DiscoveryRunNotFoundError
from src.modules.discovery.queue.job_queue import JobQueue
from src.modules.discovery.repositories.cloud_resource_repository import CloudResourceRepository
from src.modules.discovery.repositories.discovery_repository import DiscoveryRepository
from src.modules.workspace.domain.entities import Workspace
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository


class DiscoveryService:
    def __init__(
        self,
        discovery_repository: DiscoveryRepository,
        workspace_repository: WorkspaceRepository,
        *,
        queue: JobQueue | None = None,
        cloud_resource_repository: CloudResourceRepository | None = None,
    ) -> None:
        self._discovery_runs = discovery_repository
        self._workspaces = workspace_repository
        self._queue = queue
        self._cloud_resources = cloud_resource_repository

    async def run(self, workspace_id: UUID | str, current_user_id: UUID | str) -> DiscoveryRun:
        workspace = await self._ensure_workspace_access(workspace_id, current_user_id)
        started_at = datetime.now(timezone.utc)
        run = await self._discovery_runs.create(
            workspace_id=workspace.id,
            status="queued",
            summary=f"Discovery queued for workspace '{workspace.name}'.",
            resource_count=0,
            discovered_resources=[],
            started_at=started_at,
            completed_at=None,
        )
        if self._queue is not None:
            await self._queue.enqueue(
                {
                    "type": "cloud_discovery",
                    "workspace_id": str(workspace.id),
                    "discovery_run_id": str(run.id),
                }
            )
        return run

    async def list_for_workspace(self, workspace_id: UUID | str, current_user_id: UUID | str) -> list[DiscoveryRun]:
        await self._ensure_workspace_access(workspace_id, current_user_id)
        return await self._discovery_runs.list_by_workspace(workspace_id)

    async def get(self, discovery_run_id: UUID | str, current_user_id: UUID | str) -> DiscoveryRun:
        run = await self._discovery_runs.get_by_id(discovery_run_id)
        if run is None:
            raise DiscoveryRunNotFoundError(f"Discovery run '{discovery_run_id}' was not found")
        await self._ensure_workspace_access(run.workspace_id, current_user_id)
        return run

    async def list_resources_for_workspace(self, workspace_id: UUID | str, current_user_id: UUID | str) -> list[DiscoveredCloudResource]:
        await self._ensure_workspace_access(workspace_id, current_user_id)
        if self._cloud_resources is None:
            return []
        return await self._cloud_resources.list_by_workspace(workspace_id)

    async def get_resource(self, resource_id: UUID | str, current_user_id: UUID | str) -> DiscoveredCloudResource:
        resource = await self._cloud_resources.get_by_id(resource_id)
        if resource is None:
            raise DiscoveryRunNotFoundError(f"Discovered resource '{resource_id}' was not found")
        await self._ensure_workspace_access(resource.workspace_id, current_user_id)
        return resource

    async def _ensure_workspace_access(self, workspace_id: UUID | str, current_user_id: UUID | str) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' was not found")
        if str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceAccessDeniedError("You do not own this workspace")
        return workspace
