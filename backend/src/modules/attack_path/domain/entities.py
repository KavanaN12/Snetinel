from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class AttackPath:
    id: UUID
    workspace_id: UUID
    attack_type: str
    steps: list[dict[str, Any]]
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AttackPathAnalysisResult:
    workspace_id: UUID
    path_count: int
    paths: list[AttackPath] = field(default_factory=list)
