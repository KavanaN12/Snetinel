import uuid
from datetime import datetime, timezone

import pytest

from src.modules.discovery.domain.entities import DiscoveryRun
from src.modules.discovery.services.discovery_service import DiscoveryService
from src.modules.workspace.domain.entities import Workspace
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError


class FakeDiscoveryRepository:
    def __init__(self) -> None:
        self.created_runs: list[DiscoveryRun] = []

    async def create(
        self,
        *,
        workspace_id,
        status,
        summary,
        resource_count,
        discovered_resources,
        started_at,
        completed_at,
    ) -> DiscoveryRun:
        run = DiscoveryRun(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            status=status,
            summary=summary,
            resource_count=resource_count,
            discovered_resources=discovered_resources,
            started_at=started_at,
            completed_at=completed_at,
            created_at=datetime.now(timezone.utc),
        )
        self.created_runs.append(run)
        return run

    async def list_by_workspace(self, workspace_id) -> list[DiscoveryRun]:
        return [run for run in self.created_runs if run.workspace_id == workspace_id]

    async def get_by_id(self, discovery_run_id) -> DiscoveryRun | None:
        return next((run for run in self.created_runs if run.id == discovery_run_id), None)


class FakeWorkspaceRepository:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get_by_id(self, workspace_id) -> Workspace | None:
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


@pytest.mark.asyncio
async def test_run_creates_discovery_run_for_workspace_owner() -> None:
    owner_id = uuid.uuid4()
    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Alpha Workspace",
        description="Primary workspace",
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    discovery_repo = FakeDiscoveryRepository()
    workspace_repo = FakeWorkspaceRepository(workspace)
    service = DiscoveryService(discovery_repo, workspace_repo)

    run = await service.run(workspace.id, owner_id)

    assert run.status == "completed"
    assert run.workspace_id == workspace.id
    assert run.resource_count == 3
    assert "Alpha Workspace" in run.summary
    assert discovery_repo.created_runs[0].id == run.id


@pytest.mark.asyncio
async def test_run_rejects_non_owner() -> None:
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Alpha Workspace",
        description=None,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    discovery_repo = FakeDiscoveryRepository()
    workspace_repo = FakeWorkspaceRepository(workspace)
    service = DiscoveryService(discovery_repo, workspace_repo)

    with pytest.raises(WorkspaceAccessDeniedError):
        await service.run(workspace.id, other_user_id)
