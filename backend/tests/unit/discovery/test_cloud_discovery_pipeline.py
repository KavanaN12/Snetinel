import uuid
from datetime import datetime, timezone

import pytest

from src.modules.discovery.domain.entities import DiscoveryRun
from src.modules.discovery.services.discovery_service import DiscoveryService
from src.modules.workspace.domain.entities import Workspace


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[dict] = []

    async def enqueue(self, job: dict) -> None:
        self.jobs.append(job)


class FakeDiscoveryRepository:
    def __init__(self) -> None:
        self.runs: list[DiscoveryRun] = []

    async def create(self, *, workspace_id, status, summary, resource_count, discovered_resources, started_at, completed_at):
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
        self.runs.append(run)
        return run

    async def list_by_workspace(self, workspace_id):
        return [run for run in self.runs if run.workspace_id == workspace_id]

    async def get_by_id(self, discovery_run_id):
        return next((run for run in self.runs if run.id == discovery_run_id), None)


class FakeWorkspaceRepository:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get_by_id(self, workspace_id):
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


@pytest.mark.asyncio
async def test_run_enqueues_background_job_and_marks_discovery_queued() -> None:
    owner_id = uuid.uuid4()
    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Cloud Workspace",
        description="Cloud resources",
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    queue = FakeQueue()
    discovery_repo = FakeDiscoveryRepository()
    workspace_repo = FakeWorkspaceRepository(workspace)
    service = DiscoveryService(discovery_repo, workspace_repo, queue=queue)

    run = await service.run(workspace.id, owner_id)

    assert run.status == "queued"
    assert len(queue.jobs) == 1
    assert queue.jobs[0]["workspace_id"] == str(workspace.id)
    assert queue.jobs[0]["discovery_run_id"] == str(run.id)
