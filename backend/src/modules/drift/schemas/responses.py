from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DriftEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    workspace_id: str | None = None
    event_type: str
    resource_type: str
    resource_id: str
    previous_value: dict | None = None
    current_value: dict | None = None
