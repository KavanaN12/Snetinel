"""PostgreSQL implementation of the discovery repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.discovery.domain.entities import DiscoveryRun
from src.modules.discovery.infrastructure.models import DiscoveryRunModel


def _to_entity(model: DiscoveryRunModel) -> DiscoveryRun:
    return DiscoveryRun(
        id=model.id,
        workspace_id=model.workspace_id,
        status=model.status,
        summary=model.summary,
        resource_count=model.resource_count,
        discovered_resources=model.discovered_resources or [],
        started_at=model.started_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
    )


class PostgresDiscoveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID | str,
        status: str,
        summary: str,
        resource_count: int,
        discovered_resources: list[dict[str, str]],
        started_at: datetime,
        completed_at: datetime | None,
    ) -> DiscoveryRun:
        model = DiscoveryRunModel(
            workspace_id=_coerce_uuid(workspace_id),
            status=status,
            summary=summary,
            resource_count=resource_count,
            discovered_resources=discovered_resources,
            started_at=started_at,
            completed_at=completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_by_workspace(self, workspace_id: UUID | str) -> list[DiscoveryRun]:
        stmt = select(DiscoveryRunModel).where(DiscoveryRunModel.workspace_id == _coerce_uuid(workspace_id))
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [_to_entity(model) for model in models]

    async def get_by_id(self, discovery_run_id: UUID | str) -> DiscoveryRun | None:
        model = await self._session.get(DiscoveryRunModel, _coerce_uuid(discovery_run_id))
        return _to_entity(model) if model else None

    async def update_status(
        self,
        discovery_run_id: UUID | str,
        *,
        status: str | None = None,
        summary: str | None = None,
        resource_count: int | None = None,
        discovered_resources: list[dict[str, str]] | None = None,
        completed_at=None,
    ) -> DiscoveryRun | None:
        model = await self._session.get(DiscoveryRunModel, _coerce_uuid(discovery_run_id))
        if model is None:
            return None
        if status is not None:
            model.status = status
        if summary is not None:
            model.summary = summary
        if resource_count is not None:
            model.resource_count = resource_count
        if discovered_resources is not None:
            model.discovered_resources = discovered_resources
        if completed_at is not None:
            model.completed_at = completed_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
