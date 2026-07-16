"""Discovery response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    status: str = Field(default="queued")
    summary: str
    resource_count: int
    discovered_resources: list[dict[str, str]]
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime


class DiscoveredCloudResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    discovery_run_id: UUID
    resource_type: str
    resource_id: str
    name: str
    arn: str | None = None
    details: dict[str, object]
    created_at: datetime
    updated_at: datetime | None = None
