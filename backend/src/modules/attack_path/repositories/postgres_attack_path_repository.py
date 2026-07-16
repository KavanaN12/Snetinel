from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.domain.entities import AttackPath
from src.modules.attack_path.infrastructure.models import AttackPathModel
from src.modules.attack_path.repositories.attack_path_repository import AttackPathRepository


class PostgresAttackPathRepository(AttackPathRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete_for_workspace(self, workspace_id: UUID) -> None:
        await self._session.execute(AttackPathModel.__table__.delete().where(AttackPathModel.workspace_id == workspace_id))
        await self._session.commit()

    async def create(self, *, workspace_id: UUID, attack_type: str, steps: list[dict[str, Any]], details: dict[str, Any]):
        model = AttackPathModel(workspace_id=workspace_id, attack_type=attack_type, steps=steps, details=details)
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        return AttackPath(
            id=model.id,
            workspace_id=model.workspace_id,
            attack_type=model.attack_type,
            steps=model.steps or [],
            details=model.details or {},
            created_at=model.created_at,
        )

    async def list_for_workspace(self, workspace_id: UUID):
        result = await self._session.execute(select(AttackPathModel).where(AttackPathModel.workspace_id == workspace_id))
        models = result.scalars().all()
        return [
            AttackPath(
                id=model.id,
                workspace_id=model.workspace_id,
                attack_type=model.attack_type,
                steps=model.steps or [],
                details=model.details or {},
                created_at=model.created_at,
            )
            for model in models
        ]
