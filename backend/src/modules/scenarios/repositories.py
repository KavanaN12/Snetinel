from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.scenarios.infrastructure.models import ScenarioRunModel


class ScenarioRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        scenario_id: str,
        resource_manifest: dict,
        expected_results: dict,
    ) -> ScenarioRunModel:
        model = ScenarioRunModel(
            id=uuid4(),
            workspace_id=workspace_id,
            scenario_id=scenario_id,
            status="loaded",
            resource_manifest=resource_manifest,
            expected_results=expected_results,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def active_for_workspace(self, workspace_id: UUID) -> ScenarioRunModel | None:
        result = await self._session.execute(
            select(ScenarioRunModel)
            .where(
                ScenarioRunModel.workspace_id == workspace_id,
                ScenarioRunModel.status.in_(("seeding", "loaded", "failed")),
            )
            .order_by(ScenarioRunModel.created_at.desc())
        )
        return result.scalars().first()

    async def get(self, run_id: UUID) -> ScenarioRunModel | None:
        return await self._session.get(ScenarioRunModel, run_id)

    async def list_for_workspace(self, workspace_id: UUID) -> list[ScenarioRunModel]:
        result = await self._session.execute(
            select(ScenarioRunModel)
            .where(ScenarioRunModel.workspace_id == workspace_id)
            .order_by(ScenarioRunModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_reset(self, model: ScenarioRunModel) -> None:
        model.status = "reset"
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def set_actual_results(self, model: ScenarioRunModel, results: dict) -> None:
        model.actual_results = results
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
