from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.compliance.domain.entities import ComplianceFinding
from src.modules.compliance.infrastructure.models import ComplianceFindingModel


class PostgresComplianceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_result(self, *, workspace_id: UUID | str, check_id: str, title: str, description: str, severity: str, status: str, remediation: str, framework: str, details: dict) -> ComplianceFinding:
        model = ComplianceFindingModel(
            workspace_id=_coerce_uuid(workspace_id),
            check_id=check_id,
            title=title,
            description=description,
            severity=severity,
            status=status,
            remediation=remediation,
            framework=framework,
            details=details,
        )
        self._session.add(model)
        await self._session.flush()
        return ComplianceFinding(
            id=model.id,
            workspace_id=model.workspace_id,
            check_id=model.check_id,
            title=model.title,
            description=model.description,
            severity=model.severity,
            status=model.status,
            remediation=model.remediation,
            framework=model.framework,
            details=model.details or {},
            created_at=model.created_at,
        )

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[ComplianceFinding]:
        result = await self._session.execute(select(ComplianceFindingModel).where(ComplianceFindingModel.workspace_id == _coerce_uuid(workspace_id)))
        models = result.scalars().all()
        return [
            ComplianceFinding(
                id=model.id,
                workspace_id=model.workspace_id,
                check_id=model.check_id,
                title=model.title,
                description=model.description,
                severity=model.severity,
                status=model.status,
                remediation=model.remediation,
                framework=model.framework,
                details=model.details or {},
                created_at=model.created_at,
            )
            for model in models
        ]


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
