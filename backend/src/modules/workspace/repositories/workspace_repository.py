"""Abstract workspace repository contract."""

from typing import Protocol
from uuid import UUID

from src.modules.workspace.domain.entities import Workspace


class WorkspaceRepository(Protocol):
    async def create(self, owner_id: UUID | str, name: str, description: str | None) -> Workspace: ...

    async def list_by_owner(self, owner_id: UUID | str) -> list[Workspace]: ...

    async def get_by_id(self, workspace_id: UUID | str) -> Workspace | None: ...

    async def update(self, workspace_id: UUID | str, *, name: str | None = None, description: str | None = None) -> Workspace: ...

    async def delete(self, workspace_id: UUID | str) -> None: ...
