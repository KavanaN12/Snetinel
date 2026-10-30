from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IamAgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    status: str
    lifecycle: list[dict[str, Any]]
    attempts: list[dict[str, Any]]
    baseline_path_count: int
    final_path_count: int
    evaluation: dict[str, Any]
    created_at: datetime
