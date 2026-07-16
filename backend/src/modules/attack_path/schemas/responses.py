from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttackPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    attack_type: str
    steps: list[dict[str, Any]]
    details: dict[str, Any]
    created_at: datetime


class AttackPathAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    path_count: int
    paths: list[AttackPathResponse] = []
