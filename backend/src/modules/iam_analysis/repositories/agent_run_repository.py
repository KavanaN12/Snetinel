from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.iam_analysis.domain.entities import IamAgentRun


class AgentRunRepository(Protocol):
    async def create(
        self,
        *,
        workspace_id: UUID | str,
        status: str,
        lifecycle: list[dict],
        attempts: list[dict],
        baseline_path_count: int,
        final_path_count: int,
        evaluation: dict,
    ) -> IamAgentRun: ...

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[IamAgentRun]: ...
