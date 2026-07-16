from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.risk_scoring.domain.entities import Finding


class FindingRepository(Protocol):
    async def delete_for_workspace(self, workspace_id: UUID | str) -> None: ...

    async def create(
        self,
        *,
        workspace_id: UUID | str,
        title: str,
        description: str,
        severity: str,
        status: str,
        evidence_subgraph: dict,
        affected_resource_ids: list[str],
    ) -> Finding: ...

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[Finding]: ...
