from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScenarioDefinitionResponse(BaseModel):
    scenario_id: str
    name: str
    difficulty: str
    description: str
    expected_resources: list[str]
    expected_vulnerabilities: list[str]
    expected_attack_paths: str
    expected_min_paths: int
    expected_max_paths: int | None
    expected_risk: str
    expected_remediation: str
    expected_post_state: str


class ScenarioRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    scenario_id: str
    status: str
    resource_manifest: dict[str, Any]
    expected_results: dict[str, Any]
    actual_results: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None


class ScenarioLoadRequest(BaseModel):
    scenario_id: str


class ScenarioAssertionRequest(BaseModel):
    phase: Literal["baseline", "post_remediation"]


class ScenarioAssertionResponse(BaseModel):
    phase: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    passed: bool
