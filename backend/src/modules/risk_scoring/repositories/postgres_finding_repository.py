from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.risk_scoring.domain.entities import Finding
from src.modules.risk_scoring.infrastructure.models import FindingModel
from src.modules.risk_scoring.repositories.finding_repository import FindingRepository


class PostgresFindingRepository(FindingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete_for_workspace(self, workspace_id: UUID | str) -> None:
        await self._session.execute(FindingModel.__table__.delete().where(FindingModel.workspace_id == _coerce_uuid(workspace_id)))
        await self._session.commit()

    async def create(
        self,
        *,
        workspace_id: UUID | str,
        title: str,
        description: str,
        severity: str,
        status: str,
        evidence_subgraph: dict[str, Any],
        affected_resource_ids: list[str],
    ) -> Finding:
        model = FindingModel(
            workspace_id=_coerce_uuid(workspace_id),
            title=title,
            description=description,
            severity=severity,
            status=status,
            evidence_subgraph=evidence_subgraph,
            affected_resource_ids=affected_resource_ids,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        return Finding(
            id=model.id,
            workspace_id=model.workspace_id,
            title=model.title,
            description=model.description,
            severity=model.severity,
            status=model.status,
            evidence_subgraph=model.evidence_subgraph or {},
            affected_resource_ids=model.affected_resource_ids or [],
            created_at=model.created_at,
        )

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[Finding]:
        result = await self._session.execute(select(FindingModel).where(FindingModel.workspace_id == _coerce_uuid(workspace_id)))
        models = result.scalars().all()
        return [
            Finding(
                id=model.id,
                workspace_id=model.workspace_id,
                title=model.title,
                description=model.description,
                severity=model.severity,
                status=model.status,
                evidence_subgraph=model.evidence_subgraph or {},
                affected_resource_ids=model.affected_resource_ids or [],
                created_at=model.created_at,
            )
            for model in models
        ]


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
