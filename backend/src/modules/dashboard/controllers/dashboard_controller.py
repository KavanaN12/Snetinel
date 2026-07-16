from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.repositories.postgres_attack_path_repository import PostgresAttackPathRepository
from src.modules.dashboard.schemas.responses import DashboardSummaryResponse
from src.modules.dashboard.services.dashboard_service import DashboardService
from src.modules.discovery.repositories.postgres_cloud_resource_repository import PostgresCloudResourceRepository
from src.modules.risk_scoring.repositories.postgres_finding_repository import PostgresFindingRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(session: AsyncSession = Depends(get_db_session)) -> DashboardService:
    workspace_repository = PostgresWorkspaceRepository(session)
    finding_repository = PostgresFindingRepository(session)
    cloud_resource_repository = PostgresCloudResourceRepository(session)
    attack_path_repository = PostgresAttackPathRepository(session)
    return DashboardService(
        workspace_repository=workspace_repository,
        finding_repository=finding_repository,
        cloud_resource_repository=cloud_resource_repository,
        attack_path_repository=attack_path_repository,
    )


@router.get("/workspaces/{workspace_id}/summary", response_model=DashboardSummaryResponse)
async def get_summary(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    try:
        summary = await service.get_summary(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DashboardSummaryResponse(**summary)
