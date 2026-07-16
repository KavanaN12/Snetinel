"""Discovery run domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DiscoveryRun:
    id: UUID
    workspace_id: UUID
    status: str
    summary: str
    resource_count: int
    discovered_resources: list[dict[str, str]]
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
