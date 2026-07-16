from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.compliance.repositories.postgres_compliance_repository import PostgresComplianceRepository
from src.modules.compliance.schemas.responses import ComplianceEvaluationResponse
from src.modules.compliance.services.compliance_service import ComplianceService
from src.modules.discovery.repositories.postgres_cloud_resource_repository import PostgresCloudResourceRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/compliance", tags=["compliance"])


def get_compliance_service(session: AsyncSession = Depends(get_db_session)) -> ComplianceService:
    workspace_repository = PostgresWorkspaceRepository(session)
    cloud_resource_repository = PostgresCloudResourceRepository(session)
    compliance_repository = PostgresComplianceRepository(session)
    return ComplianceService(
        workspace_repository=workspace_repository,
        cloud_resource_repository=cloud_resource_repository,
        compliance_repository=compliance_repository,
    )


@router.post("/workspaces/{workspace_id}/evaluate", response_model=ComplianceEvaluationResponse)
async def evaluate_workspace(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: ComplianceService = Depends(get_compliance_service),
) -> ComplianceEvaluationResponse:
    try:
        result = await service.evaluate_workspace(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ComplianceEvaluationResponse(**result)
