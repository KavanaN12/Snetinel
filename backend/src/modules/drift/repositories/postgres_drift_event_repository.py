from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.drift.domain.entities import DriftEvent
from src.modules.drift.infrastructure.models import DriftEventModel


class PostgresDriftEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_event(self, *, workspace_id: UUID | str, event_type: str, resource_type: str, resource_id: str, previous_value: dict | None, current_value: dict | None) -> DriftEvent:
        model = DriftEventModel(
            workspace_id=_coerce_uuid(workspace_id),
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            previous_value=previous_value,
            current_value=current_value,
        )
        self._session.add(model)
        await self._session.flush()
        return DriftEvent(
            id=model.id,
            workspace_id=model.workspace_id,
            event_type=model.event_type,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            previous_value=model.previous_value,
            current_value=model.current_value,
            created_at=model.created_at,
        )

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[DriftEvent]:
        result = await self._session.execute(select(DriftEventModel).where(DriftEventModel.workspace_id == _coerce_uuid(workspace_id)))
        models = result.scalars().all()
        return [
            DriftEvent(
                id=model.id,
                workspace_id=model.workspace_id,
                event_type=model.event_type,
                resource_type=model.resource_type,
                resource_id=model.resource_id,
                previous_value=model.previous_value,
                current_value=model.current_value,
                created_at=model.created_at,
            )
            for model in models
        ]


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
