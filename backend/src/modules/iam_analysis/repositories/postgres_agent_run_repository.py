from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.iam_analysis.domain.entities import IamAgentRun
from src.modules.iam_analysis.infrastructure.models import IamAgentRunModel


class PostgresAgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
    ) -> IamAgentRun:
        model = IamAgentRunModel(
            workspace_id=UUID(str(workspace_id)),
            status=status,
            lifecycle=lifecycle,
            attempts=attempts,
            baseline_path_count=baseline_path_count,
            final_path_count=final_path_count,
            evaluation=evaluation,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[IamAgentRun]:
        statement = (
            select(IamAgentRunModel)
            .where(IamAgentRunModel.workspace_id == UUID(str(workspace_id)))
            .order_by(IamAgentRunModel.created_at.desc())
        )
        result = await self._session.execute(statement)
        return [self._to_entity(model) for model in result.scalars().all()]

    @staticmethod
    def _to_entity(model: IamAgentRunModel) -> IamAgentRun:
        return IamAgentRun(
            id=model.id,
            workspace_id=model.workspace_id,
            status=model.status,
            lifecycle=model.lifecycle or [],
            attempts=model.attempts or [],
            baseline_path_count=model.baseline_path_count,
            final_path_count=model.final_path_count,
            evaluation=model.evaluation or {},
            created_at=model.created_at,
        )
