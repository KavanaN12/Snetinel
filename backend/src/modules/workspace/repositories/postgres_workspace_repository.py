"""PostgreSQL implementation of the workspace repository."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.workspace.domain.entities import Workspace
from src.modules.workspace.infrastructure.models import WorkspaceModel


def _to_entity(model: WorkspaceModel) -> Workspace:
    return Workspace(
        id=model.id,
        owner_id=model.owner_id,
        name=model.name,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class PostgresWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, owner_id: UUID | str, name: str, description: str | None) -> Workspace:
        model = WorkspaceModel(owner_id=_coerce_uuid(owner_id), name=name, description=description)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_by_owner(self, owner_id: UUID | str) -> list[Workspace]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.owner_id == _coerce_uuid(owner_id))
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [_to_entity(model) for model in models]

    async def get_by_id(self, workspace_id: UUID | str) -> Workspace | None:
        model = await self._session.get(WorkspaceModel, _coerce_uuid(workspace_id))
        return _to_entity(model) if model else None

    async def update(self, workspace_id: UUID | str, *, name: str | None = None, description: str | None = None) -> Workspace:
        model = await self._session.get(WorkspaceModel, _coerce_uuid(workspace_id))
        if model is None:
            raise LookupError("Workspace not found")
        if name is not None:
            model.name = name
        if description is not None:
            model.description = description
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, workspace_id: UUID | str) -> None:
        model = await self._session.get(WorkspaceModel, _coerce_uuid(workspace_id))
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
