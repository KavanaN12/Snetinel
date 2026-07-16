from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class AIExplanationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    workspace_id: str | None = None
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    evidence_subgraph: dict[str, Any] | None = None
    affected_resource_ids: list[str] | None = None
