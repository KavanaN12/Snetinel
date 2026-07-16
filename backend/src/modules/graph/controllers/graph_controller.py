from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.graph.schemas.responses import GraphResponse
from src.modules.graph.services.graph_service import GraphService
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.modules.graph.repositories.postgres_graph_repository import PostgresGraphRepository
from src.modules.discovery.repositories.postgres_cloud_resource_repository import PostgresCloudResourceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/graph", tags=["graph"])


def get_graph_service(session: AsyncSession = Depends(get_db_session)) -> GraphService:
    workspace_repository = PostgresWorkspaceRepository(session)
    cloud_resource_repository = PostgresCloudResourceRepository(session)
    graph_repository = PostgresGraphRepository(session)
    return GraphService(
        workspace_repository=workspace_repository,
        cloud_resource_repository=cloud_resource_repository,
        graph_repository=graph_repository,
    )


@router.post("/workspaces/{workspace_id}/build", response_model=GraphResponse)
async def build_graph(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: GraphService = Depends(get_graph_service),
) -> GraphResponse:
    try:
        result = await service.build_graph(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return GraphResponse(
        workspace_id=result.workspace_id,
        node_count=result.node_count,
        edge_count=result.edge_count,
        nodes=[
            {
                "id": node.id,
                "workspace_id": node.workspace_id,
                "node_type": node.node_type,
                "external_id": node.external_id,
                "name": node.name,
                "details": node.details,
            }
            for node in result.nodes
        ],
        edges=[
            {
                "id": edge.id,
                "workspace_id": edge.workspace_id,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "edge_type": edge.edge_type,
                "details": edge.details,
            }
            for edge in result.edges
        ],
    )


@router.get("/workspaces/{workspace_id}", response_model=GraphResponse)
async def list_graph(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: GraphService = Depends(get_graph_service),
) -> GraphResponse:
    try:
        result = await service.list_graph(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return GraphResponse(
        workspace_id=result.workspace_id,
        node_count=result.node_count,
        edge_count=result.edge_count,
        nodes=[
            {
                "id": node.id,
                "workspace_id": node.workspace_id,
                "node_type": node.node_type,
                "external_id": node.external_id,
                "name": node.name,
                "details": node.details,
            }
            for node in result.nodes
        ],
        edges=[
            {
                "id": edge.id,
                "workspace_id": edge.workspace_id,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "edge_type": edge.edge_type,
                "details": edge.details,
            }
            for edge in result.edges
        ],
    )
