from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(slots=True)
class DriftEvent:
    id: UUID | None = None
    workspace_id: UUID | None = None
    event_type: str = "added"
    resource_type: str = ""
    resource_id: str = ""
    previous_value: dict | None = None
    current_value: dict | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class DriftSnapshot:
    id: UUID | None = None
    workspace_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
