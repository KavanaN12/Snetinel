from __future__ import annotations

from uuid import UUID

from src.modules.audit.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self._audit_log_repository = audit_log_repository

    async def log_event(
        self,
        *,
        actor_id: UUID | str,
        action: str,
        resource: str,
        method: str,
        path: str,
        status_code: int,
    ) -> None:
        await self._audit_log_repository.create(
            actor_id=actor_id,
            action=action,
            resource=resource,
            method=method,
            path=path,
            status_code=status_code,
        )

    async def list_for_actor(self, actor_id: UUID | str) -> list[object]:
        return await self._audit_log_repository.list_for_actor(actor_id)
