from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.audit.domain.entities import AuditLog


class AuditLogRepository(Protocol):
    async def create(
        self,
        *,
        actor_id: UUID | str,
        action: str,
        resource: str,
        method: str,
        path: str,
        status_code: int,
    ) -> AuditLog: ...

    async def list_for_actor(self, actor_id: UUID | str) -> list[AuditLog]: ...
