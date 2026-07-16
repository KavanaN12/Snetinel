"""Discovery controller."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.discovery.domain.exceptions import DiscoveryRunNotFoundError
from src.modules.discovery.repositories.postgres_discovery_repository import PostgresDiscoveryRepository
from src.modules.discovery.schemas.requests import DiscoveryRunRequest
from src.modules.discovery.schemas.responses import DiscoveryRunResponse
from src.modules.discovery.services.discovery_service import DiscoveryService
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/discovery", tags=["discovery"])


def get_discovery_service(session: AsyncSession = Depends(get_db_session)) -> DiscoveryService:
    discovery_repository = PostgresDiscoveryRepository(session)
    workspace_repository = PostgresWorkspaceRepository(session)
    return DiscoveryService(discovery_repository, workspace_repository)


@router.post("/workspaces/{workspace_id}/discover", response_model=DiscoveryRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_discovery(
    workspace_id: UUID,
    request: DiscoveryRunRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryRunResponse:
    try:
        run = await service.run(workspace_id=workspace_id, current_user_id=current_user_id)
        await session.commit()
    except WorkspaceNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return DiscoveryRunResponse.model_validate(run, from_attributes=True)


@router.get("/workspaces/{workspace_id}/runs", response_model=list[DiscoveryRunResponse])
async def list_discovery_runs(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: DiscoveryService = Depends(get_discovery_service),
) -> list[DiscoveryRunResponse]:
    try:
        runs = await service.list_for_workspace(workspace_id=workspace_id, current_user_id=current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [DiscoveryRunResponse.model_validate(run, from_attributes=True) for run in runs]


@router.get("/runs/{discovery_run_id}", response_model=DiscoveryRunResponse)
async def get_discovery_run(
    discovery_run_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryRunResponse:
    try:
        run = await service.get(discovery_run_id=discovery_run_id, current_user_id=current_user_id)
    except DiscoveryRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return DiscoveryRunResponse.model_validate(run, from_attributes=True)
