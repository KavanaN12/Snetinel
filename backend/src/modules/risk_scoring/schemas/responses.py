from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    description: str
    severity: str
    status: str
    evidence_subgraph: dict[str, Any]
    affected_resource_ids: list[str]


class FindingEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    finding_count: int
    findings: list[FindingResponse] = []
