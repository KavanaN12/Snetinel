"""Discovery-related domain entities."""

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


@dataclass(frozen=True)
class DiscoveredCloudResource:
    id: UUID
    workspace_id: UUID
    discovery_run_id: UUID
    resource_type: str
    resource_id: str
    name: str
    arn: str | None
    details: dict[str, object]
    created_at: datetime
    updated_at: datetime | None
