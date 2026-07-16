from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.compliance.domain.entities import ComplianceFinding


class ComplianceRepository(Protocol):
    async def create_result(self, *, workspace_id: UUID | str, check_id: str, title: str, description: str, severity: str, status: str, remediation: str, framework: str, details: dict) -> ComplianceFinding: ...

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[ComplianceFinding]: ...
