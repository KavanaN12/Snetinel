"""Discovery service layer."""

from datetime import datetime, timezone
from uuid import UUID

from src.modules.discovery.domain.entities import DiscoveryRun
from src.modules.discovery.domain.exceptions import DiscoveryAccessDeniedError, DiscoveryRunNotFoundError
from src.modules.discovery.repositories.discovery_repository import DiscoveryRepository
from src.modules.workspace.domain.entities import Workspace
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository


class DiscoveryService:
    def __init__(
        self,
        discovery_repository: DiscoveryRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._discovery_runs = discovery_repository
        self._workspaces = workspace_repository

    async def run(self, workspace_id: UUID | str, current_user_id: UUID | str) -> DiscoveryRun:
        workspace = await self._ensure_workspace_access(workspace_id, current_user_id)
        started_at = datetime.now(timezone.utc)
        summary = self._build_summary(workspace)
        discovered_resources = self._build_resources(workspace)
        run = await self._discovery_runs.create(
            workspace_id=workspace.id,
            status="completed",
            summary=summary,
            resource_count=len(discovered_resources),
            discovered_resources=discovered_resources,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
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

    async def _ensure_workspace_access(self, workspace_id: UUID | str, current_user_id: UUID | str) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' was not found")
        if str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceAccessDeniedError("You do not own this workspace")
        return workspace

    @staticmethod
    def _build_summary(workspace: Workspace) -> str:
        return f"Discovered workspace '{workspace.name}' for owner '{workspace.owner_id}'."

    @staticmethod
    def _build_resources(workspace: Workspace) -> list[dict[str, str]]:
        resources = [{"type": "workspace", "name": workspace.name}]
        if workspace.description:
            resources.append({"type": "description", "name": workspace.description})
        resources.append({"type": "owner", "name": str(workspace.owner_id)})
        return resources
