"""Workspace controller."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.modules.workspace.schemas.requests import CreateWorkspaceRequest, UpdateWorkspaceRequest
from src.modules.workspace.schemas.responses import WorkspaceResponse
from src.modules.workspace.services.workspace_service import WorkspaceService
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_service(session: AsyncSession = Depends(get_db_session)) -> WorkspaceService:
    workspace_repo = PostgresWorkspaceRepository(session)
    return WorkspaceService(workspace_repository=workspace_repo)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: CreateWorkspaceRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    workspace = await workspace_service.create(owner_id=current_user_id, name=payload.name, description=payload.description)
    await session.commit()
    return WorkspaceResponse.model_validate(workspace, from_attributes=True)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    session: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> list[WorkspaceResponse]:
    workspaces = await workspace_service.list(owner_id=current_user_id)
    await session.commit()
    return [WorkspaceResponse.model_validate(workspace, from_attributes=True) for workspace in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    try:
        workspace = await workspace_service.get(workspace_id=workspace_id, current_user_id=current_user_id)
    except WorkspaceNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return WorkspaceResponse.model_validate(workspace, from_attributes=True)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    payload: UpdateWorkspaceRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    try:
        workspace = await workspace_service.update(
            workspace_id=workspace_id,
            current_user_id=current_user_id,
            name=payload.name,
            description=payload.description,
        )
        await session.commit()
    except WorkspaceNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return WorkspaceResponse.model_validate(workspace, from_attributes=True)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    try:
        await workspace_service.delete(workspace_id=workspace_id, current_user_id=current_user_id)
        await session.commit()
    except WorkspaceNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
