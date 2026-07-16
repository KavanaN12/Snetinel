from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class ComplianceFinding:
    id: UUID | None = None
    workspace_id: UUID | None = None
    check_id: str = ""
    title: str = ""
    description: str = ""
    severity: str = "low"
    status: str = "failed"
    remediation: str = ""
    framework: str = "cis-aws"
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(slots=True)
class ComplianceSummary:
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
