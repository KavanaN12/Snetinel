"""Response schemas for workspace endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WorkspaceResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
