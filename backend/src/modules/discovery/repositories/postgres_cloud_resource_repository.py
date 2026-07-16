"""PostgreSQL implementation of the cloud resource repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.discovery.domain.entities import DiscoveredCloudResource
from src.modules.discovery.infrastructure.models import CloudDiscoveredResourceModel


def _to_entity(model: CloudDiscoveredResourceModel) -> DiscoveredCloudResource:
    return DiscoveredCloudResource(
        id=model.id,
        workspace_id=model.workspace_id,
        discovery_run_id=model.discovery_run_id,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        name=model.name,
        arn=model.arn,
        details=model.details or {},
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class PostgresCloudResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_or_update(
        self,
        *,
        workspace_id: UUID | str,
        discovery_run_id: UUID | str,
        resource_type: str,
        resource_id: str,
        name: str,
        arn: str | None,
        details: dict[str, object],
    ) -> DiscoveredCloudResource:
        workspace_uuid = _coerce_uuid(workspace_id)
        discovery_run_uuid = _coerce_uuid(discovery_run_id)
        stmt = select(CloudDiscoveredResourceModel).where(
            CloudDiscoveredResourceModel.workspace_id == workspace_uuid,
            CloudDiscoveredResourceModel.resource_type == resource_type,
            CloudDiscoveredResourceModel.resource_id == resource_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        if model is None:
            model = CloudDiscoveredResourceModel(
                workspace_id=workspace_uuid,
                discovery_run_id=discovery_run_uuid,
                resource_type=resource_type,
                resource_id=resource_id,
                name=name,
                arn=arn,
                details=details,
            )
            self._session.add(model)
        else:
            model.discovery_run_id = discovery_run_uuid
            model.name = name
            model.arn = arn
            model.details = details
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_by_workspace(self, workspace_id: UUID | str) -> list[DiscoveredCloudResource]:
        stmt = select(CloudDiscoveredResourceModel).where(CloudDiscoveredResourceModel.workspace_id == _coerce_uuid(workspace_id))
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [_to_entity(model) for model in models]

    async def get_by_id(self, resource_id: UUID | str) -> DiscoveredCloudResource | None:
        model = await self._session.get(CloudDiscoveredResourceModel, _coerce_uuid(resource_id))
        return _to_entity(model) if model else None


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
