"""Background worker that consumes discovery jobs from the queue."""

from __future__ import annotations

import asyncio
from typing import Any

from src.modules.discovery.queue.job_queue import RedisJobQueue
from src.modules.discovery.repositories.postgres_cloud_resource_repository import PostgresCloudResourceRepository
from src.modules.discovery.repositories.postgres_discovery_repository import PostgresDiscoveryRepository
from src.modules.discovery.services.cloud_discovery_service import CloudDiscoveryService
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import AsyncSessionLocal


class DiscoveryWorker:
    def __init__(self, queue: RedisJobQueue | None = None) -> None:
        self._queue = queue or RedisJobQueue()

    async def run(self) -> None:
        while True:
            job = await self._queue.dequeue()
            if job is None:
                await asyncio.sleep(1)
                continue
            await self._process_job(job)

    async def _process_job(self, job: dict[str, Any]) -> None:
        discovery_run_id = job.get("discovery_run_id")
        workspace_id = job.get("workspace_id")
        if not discovery_run_id or not workspace_id:
            return

        async with AsyncSessionLocal() as session:
            discovery_repository = PostgresDiscoveryRepository(session)
            workspace_repository = PostgresWorkspaceRepository(session)
            cloud_resource_repository = PostgresCloudResourceRepository(session)
            cloud_discovery_service = CloudDiscoveryService(
                discovery_repository=discovery_repository,
                workspace_repository=workspace_repository,
                cloud_resource_repository=cloud_resource_repository,
            )
            try:
                await cloud_discovery_service.process_discovery_job(workspace_id=workspace_id, discovery_run_id=discovery_run_id)
                await session.commit()
            except Exception:
                await session.rollback()
                raise


async def main() -> None:
    worker = DiscoveryWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
