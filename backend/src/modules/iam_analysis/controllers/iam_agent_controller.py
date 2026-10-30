from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.repositories.postgres_attack_path_repository import PostgresAttackPathRepository
from src.modules.discovery.repositories.postgres_cloud_resource_repository import PostgresCloudResourceRepository
from src.modules.discovery.repositories.postgres_discovery_repository import PostgresDiscoveryRepository
from src.modules.graph.repositories.postgres_graph_repository import PostgresGraphRepository
from src.modules.iam_analysis.remediation import LocalStackEndpointError
from src.modules.iam_analysis.repositories.postgres_agent_run_repository import PostgresAgentRunRepository
from src.modules.iam_analysis.schemas.requests import IamAgentRunRequest
from src.modules.iam_analysis.schemas.responses import IamAgentRunResponse
from src.modules.iam_analysis.services.iam_agent_service import IamAgentService
from src.modules.risk_scoring.repositories.postgres_finding_repository import PostgresFindingRepository
from src.modules.scenarios.repositories import ScenarioRunRepository
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/iam-agent", tags=["iam-agent"])


def get_iam_agent_service(
    session: AsyncSession = Depends(get_db_session),
) -> IamAgentService:
    return IamAgentService(
        session=session,
        workspace_repository=PostgresWorkspaceRepository(session),
        discovery_repository=PostgresDiscoveryRepository(session),
        cloud_resource_repository=PostgresCloudResourceRepository(session),
        graph_repository=PostgresGraphRepository(session),
        attack_path_repository=PostgresAttackPathRepository(session),
        finding_repository=PostgresFindingRepository(session),
        agent_run_repository=PostgresAgentRunRepository(session),
        scenario_run_repository=ScenarioRunRepository(session),
    )


@router.post(
    "/workspaces/{workspace_id}/run",
    response_model=IamAgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_iam_agent(
    workspace_id: UUID,
    request: IamAgentRunRequest,
    current_user_id: str = Depends(get_current_user_id),
    service: IamAgentService = Depends(get_iam_agent_service),
) -> IamAgentRunResponse:
    try:
        run = await service.run(
            workspace_id,
            current_user_id,
            max_attempts=request.max_attempts,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LocalStackEndpointError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return IamAgentRunResponse.model_validate(run, from_attributes=True)


@router.get(
    "/workspaces/{workspace_id}/runs",
    response_model=list[IamAgentRunResponse],
)
async def list_iam_agent_runs(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: IamAgentService = Depends(get_iam_agent_service),
) -> list[IamAgentRunResponse]:
    try:
        runs = await service.list_runs(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [IamAgentRunResponse.model_validate(run, from_attributes=True) for run in runs]
