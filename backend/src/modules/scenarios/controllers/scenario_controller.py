from __future__ import annotations

from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.repositories.postgres_attack_path_repository import PostgresAttackPathRepository
from src.modules.attack_path.services.attack_path_service import AttackPathService
from src.modules.discovery.repositories.postgres_cloud_resource_repository import PostgresCloudResourceRepository
from src.modules.graph.repositories.postgres_graph_repository import PostgresGraphRepository
from src.modules.graph.services.graph_service import GraphService
from src.modules.iam_analysis.remediation import LocalStackEndpointError
from src.modules.scenarios.repositories import ScenarioRunRepository
from src.modules.scenarios.schemas import (
    ScenarioAssertionRequest,
    ScenarioAssertionResponse,
    ScenarioDefinitionResponse,
    ScenarioLoadRequest,
    ScenarioRunResponse,
)
from src.modules.scenarios.service import ScenarioConflictError, ScenarioService
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def get_scenario_service(
    session: AsyncSession = Depends(get_db_session),
) -> ScenarioService:
    return ScenarioService(
        session=session,
        workspace_repository=PostgresWorkspaceRepository(session),
        scenario_repository=ScenarioRunRepository(session),
    )


@router.get("/catalog", response_model=list[ScenarioDefinitionResponse])
async def list_scenarios(
    current_user_id: str = Depends(get_current_user_id),
) -> list[ScenarioDefinitionResponse]:
    del current_user_id
    return [
        ScenarioDefinitionResponse.model_validate(item)
        for item in ScenarioService.list_catalog()
    ]


@router.get(
    "/workspaces/{workspace_id}/runs",
    response_model=list[ScenarioRunResponse],
)
async def list_scenario_runs(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: ScenarioService = Depends(get_scenario_service),
) -> list[ScenarioRunResponse]:
    try:
        runs = await service.list_runs(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [ScenarioRunResponse.model_validate(run, from_attributes=True) for run in runs]


@router.post(
    "/workspaces/{workspace_id}/runs",
    response_model=ScenarioRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def load_scenario(
    workspace_id: UUID,
    request: ScenarioLoadRequest,
    current_user_id: str = Depends(get_current_user_id),
    service: ScenarioService = Depends(get_scenario_service),
) -> ScenarioRunResponse:
    try:
        run = await service.load(workspace_id, current_user_id, request.scenario_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ScenarioConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LocalStackEndpointError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"LocalStack scenario load failed: {exc}") from exc
    return ScenarioRunResponse.model_validate(run, from_attributes=True)


@router.post(
    "/workspaces/{workspace_id}/runs/{run_id}/assertions",
    response_model=ScenarioAssertionResponse,
)
async def assert_scenario_results(
    workspace_id: UUID,
    run_id: UUID,
    request: ScenarioAssertionRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
    service: ScenarioService = Depends(get_scenario_service),
) -> ScenarioAssertionResponse:
    graph_service = GraphService(
        workspace_repository=PostgresWorkspaceRepository(session),
        cloud_resource_repository=PostgresCloudResourceRepository(session),
        graph_repository=PostgresGraphRepository(session),
    )
    attack_path_service = AttackPathService(
        workspace_repository=PostgresWorkspaceRepository(session),
        graph_repository=PostgresGraphRepository(session),
        attack_path_repository=PostgresAttackPathRepository(session),
    )
    try:
        graph = await graph_service.list_graph(workspace_id, current_user_id)
        paths = await attack_path_service.list_paths(workspace_id, current_user_id)
        result = await service.record_assertion(
            workspace_id,
            current_user_id,
            run_id,
            phase=request.phase,
            nodes=graph.nodes,
            paths=paths.paths,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ScenarioAssertionResponse.model_validate(result)


@router.post(
    "/workspaces/{workspace_id}/runs/{run_id}/reset",
    response_model=ScenarioRunResponse,
)
async def reset_scenario(
    workspace_id: UUID,
    run_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: ScenarioService = Depends(get_scenario_service),
) -> ScenarioRunResponse:
    try:
        run = await service.reset(workspace_id, current_user_id, run_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceAccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LocalStackEndpointError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"LocalStack scenario reset failed: {exc}") from exc
    return ScenarioRunResponse.model_validate(run, from_attributes=True)
