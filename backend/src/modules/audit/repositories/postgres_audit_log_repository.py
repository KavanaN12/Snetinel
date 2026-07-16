from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.audit.domain.entities import AuditLog
from src.modules.audit.infrastructure.models import AuditLogModel
from src.modules.audit.repositories.audit_log_repository import AuditLogRepository


class PostgresAuditLogRepository(AuditLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        actor_id: UUID | str,
        action: str,
        resource: str,
        method: str,
        path: str,
        status_code: int,
    ) -> AuditLog:
        model = AuditLogModel(
            actor_id=_coerce_uuid(actor_id),
            action=action,
            resource=resource,
            method=method,
            path=path,
            status_code=status_code,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        return AuditLog(
            id=model.id,
            actor_id=model.actor_id,
            action=model.action,
            resource=model.resource,
            method=model.method,
            path=model.path,
            status_code=model.status_code,
            created_at=model.created_at,
        )

    async def list_for_actor(self, actor_id: UUID | str) -> list[AuditLog]:
        result = await self._session.execute(select(AuditLogModel).where(AuditLogModel.actor_id == _coerce_uuid(actor_id)))
        models = result.scalars().all()
        return [
            AuditLog(
                id=model.id,
                actor_id=model.actor_id,
                action=model.action,
                resource=model.resource,
                method=model.method,
                path=model.path,
                status_code=model.status_code,
                created_at=model.created_at,
            )
            for model in models
        ]


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
