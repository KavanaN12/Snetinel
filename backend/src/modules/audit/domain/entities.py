from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(slots=True)
class AuditLog:
    id: UUID
    actor_id: UUID | str
    action: str
    resource: str
    method: str
    path: str
    status_code: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
