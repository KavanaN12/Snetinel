import uuid

import pytest

from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.services.workspace_service import WorkspaceService


class FakeWorkspaceRepository:
    def __init__(self) -> None:
        self._workspaces = {}

    async def create(self, owner_id, name, description):
        workspace = type(
            "Workspace",
            (),
            {
                "id": str(uuid.uuid4()),
                "owner_id": owner_id,
                "name": name,
                "description": description,
                "created_at": None,
                "updated_at": None,
            },
        )()
        self._workspaces[workspace.id] = workspace
        return workspace

    async def list_by_owner(self, owner_id):
        return [w for w in self._workspaces.values() if w.owner_id == owner_id]

    async def get_by_id(self, workspace_id):
        return self._workspaces.get(workspace_id)

    async def update(self, workspace_id, *, name=None, description=None):
        workspace = self._workspaces[workspace_id]
        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description
        return workspace

    async def delete(self, workspace_id):
        self._workspaces.pop(workspace_id, None)


@pytest.fixture
def workspace_service() -> WorkspaceService:
    return WorkspaceService(workspace_repository=FakeWorkspaceRepository())


@pytest.mark.asyncio
async def test_create_workspace_assigns_owner(workspace_service):
    workspace = await workspace_service.create(owner_id="owner-1", name="Alpha", description="First")

    assert workspace.name == "Alpha"
    assert workspace.owner_id == "owner-1"


@pytest.mark.asyncio
async def test_list_returns_only_owner_workspaces(workspace_service):
    await workspace_service.create(owner_id="owner-1", name="Alpha", description="First")
    await workspace_service.create(owner_id="owner-2", name="Beta", description="Second")

    workspaces = await workspace_service.list(owner_id="owner-1")

    assert len(workspaces) == 1
    assert workspaces[0].name == "Alpha"


@pytest.mark.asyncio
async def test_get_requires_owner_access(workspace_service):
    workspace = await workspace_service.create(owner_id="owner-1", name="Alpha", description="First")

    with pytest.raises(WorkspaceAccessDeniedError):
        await workspace_service.get(workspace_id=workspace.id, current_user_id="owner-2")


@pytest.mark.asyncio
async def test_update_and_delete_only_for_owner(workspace_service):
    workspace = await workspace_service.create(owner_id="owner-1", name="Alpha", description="First")

    updated = await workspace_service.update(workspace_id=workspace.id, current_user_id="owner-1", name="Updated")
    assert updated.name == "Updated"

    with pytest.raises(WorkspaceAccessDeniedError):
        await workspace_service.delete(workspace_id=workspace.id, current_user_id="owner-2")

    await workspace_service.delete(workspace_id=workspace.id, current_user_id="owner-1")

    with pytest.raises(WorkspaceNotFoundError):
        await workspace_service.get(workspace_id=workspace.id, current_user_id="owner-1")
