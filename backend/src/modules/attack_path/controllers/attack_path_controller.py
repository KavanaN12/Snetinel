from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.schemas.responses import AttackPathAnalysisResponse
from src.modules.attack_path.services.attack_path_service import AttackPathService
from src.modules.attack_path.repositories.postgres_attack_path_repository import PostgresAttackPathRepository
from src.modules.graph.repositories.postgres_graph_repository import PostgresGraphRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/attack-path", tags=["attack-path"])


def get_attack_path_service(session: AsyncSession = Depends(get_db_session)) -> AttackPathService:
    workspace_repository = PostgresWorkspaceRepository(session)
    graph_repository = PostgresGraphRepository(session)
    attack_path_repository = PostgresAttackPathRepository(session)
    return AttackPathService(
        workspace_repository=workspace_repository,
        graph_repository=graph_repository,
        attack_path_repository=attack_path_repository,
    )


@router.post("/workspaces/{workspace_id}/analyze", response_model=AttackPathAnalysisResponse)
async def analyze_attack_paths(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: AttackPathService = Depends(get_attack_path_service),
) -> AttackPathAnalysisResponse:
    try:
        result = await service.analyze(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AttackPathAnalysisResponse(
        workspace_id=result.workspace_id,
        path_count=result.path_count,
        paths=[
            {
                "id": path.id,
                "workspace_id": path.workspace_id,
                "attack_type": path.attack_type,
                "steps": path.steps,
                "details": path.details,
                "created_at": path.created_at,
            }
            for path in result.paths
        ],
    )


@router.get("/workspaces/{workspace_id}", response_model=AttackPathAnalysisResponse)
async def list_attack_paths(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: AttackPathService = Depends(get_attack_path_service),
) -> AttackPathAnalysisResponse:
    try:
        result = await service.list_paths(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AttackPathAnalysisResponse(
        workspace_id=result.workspace_id,
        path_count=result.path_count,
        paths=[
            {
                "id": path.id,
                "workspace_id": path.workspace_id,
                "attack_type": path.attack_type,
                "steps": path.steps,
                "details": path.details,
                "created_at": path.created_at,
            }
            for path in result.paths
        ],
    )
