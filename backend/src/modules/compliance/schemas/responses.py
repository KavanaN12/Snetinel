from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ComplianceFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    workspace_id: UUID | None = None
    check_id: str
    title: str
    description: str
    severity: str
    status: str
    remediation: str
    framework: str
    details: dict


class ComplianceEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID | None = None
    summary: dict
    findings: list[ComplianceFindingResponse]
