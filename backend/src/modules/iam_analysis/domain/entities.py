from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class IamAgentRun:
    id: UUID
    workspace_id: UUID
    status: str
    lifecycle: list[dict[str, Any]]
    attempts: list[dict[str, Any]]
    baseline_path_count: int
    final_path_count: int
    evaluation: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
