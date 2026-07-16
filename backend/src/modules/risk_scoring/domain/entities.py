from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class Finding:
    id: UUID
    workspace_id: UUID
    title: str
    description: str
    severity: str
    status: str
    evidence_subgraph: dict[str, Any] = field(default_factory=dict)
    affected_resource_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class FindingEvaluationResult:
    workspace_id: UUID
    finding_count: int
    findings: list[Finding] = field(default_factory=list)
