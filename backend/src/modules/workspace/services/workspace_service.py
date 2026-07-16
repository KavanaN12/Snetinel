"""Workspace service layer."""

from uuid import UUID

from src.modules.workspace.domain.entities import Workspace
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository


class WorkspaceService:
    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self._workspaces = workspace_repository

    async def create(self, owner_id: UUID | str, name: str, description: str | None = None) -> Workspace:
        normalized_name = name.strip()
        normalized_description = description.strip() if description is not None else None
        return await self._workspaces.create(owner_id=owner_id, name=normalized_name, description=normalized_description)

    async def list(self, owner_id: UUID | str) -> list[Workspace]:
        return await self._workspaces.list_by_owner(owner_id)

    async def get(self, workspace_id: UUID | str, current_user_id: UUID | str) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' was not found")
        if str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceAccessDeniedError("You do not own this workspace")
        return workspace

    async def update(
        self,
        workspace_id: UUID | str,
        current_user_id: UUID | str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Workspace:
        await self.get(workspace_id, current_user_id)
        return await self._workspaces.update(
            workspace_id,
            name=name.strip() if name is not None else None,
            description=description.strip() if description is not None else None,
        )

    async def delete(self, workspace_id: UUID | str, current_user_id: UUID | str) -> None:
        await self.get(workspace_id, current_user_id)
        await self._workspaces.delete(workspace_id)
