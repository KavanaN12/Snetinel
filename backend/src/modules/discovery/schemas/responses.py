"""Discovery response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    status: str = Field(default="completed")
    summary: str
    resource_count: int
    discovered_resources: list[dict[str, str]]
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
