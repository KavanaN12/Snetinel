from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.graph.domain.entities import GraphEdge, GraphNode
from src.modules.graph.infrastructure.models import GraphEdgeModel, GraphNodeModel
from src.modules.graph.repositories.graph_repository import GraphRepository


class PostgresGraphRepository(GraphRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete_for_workspace(self, workspace_id: UUID) -> None:
        await self._session.execute(select(GraphEdgeModel).where(GraphEdgeModel.workspace_id == workspace_id))
        await self._session.execute(select(GraphNodeModel).where(GraphNodeModel.workspace_id == workspace_id))
        await self._session.execute(
            GraphEdgeModel.__table__.delete().where(GraphEdgeModel.workspace_id == workspace_id)
        )
        await self._session.execute(
            GraphNodeModel.__table__.delete().where(GraphNodeModel.workspace_id == workspace_id)
        )
        await self._session.commit()

    async def create_node(self, *, workspace_id: UUID, node_type: str, external_id: str, name: str, details: dict[str, Any]):
        model = GraphNodeModel(
            workspace_id=workspace_id,
            node_type=node_type,
            external_id=external_id,
            name=name,
            details=details,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        return GraphNode(
            id=model.id,
            workspace_id=model.workspace_id,
            node_type=model.node_type,
            external_id=model.external_id,
            name=model.name,
            details=model.details or {},
            created_at=model.created_at,
        )

    async def create_edge(self, *, workspace_id: UUID, source_node_id: UUID, target_node_id: UUID, edge_type: str, details: dict[str, Any]):
        model = GraphEdgeModel(
            workspace_id=workspace_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            details=details,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        return GraphEdge(
            id=model.id,
            workspace_id=model.workspace_id,
            source_node_id=model.source_node_id,
            target_node_id=model.target_node_id,
            edge_type=model.edge_type,
            details=model.details or {},
            created_at=model.created_at,
        )

    async def list_nodes(self, workspace_id: UUID):
        result = await self._session.execute(
            select(GraphNodeModel).where(GraphNodeModel.workspace_id == workspace_id)
        )
        models = result.scalars().all()
        return [
            GraphNode(
                id=model.id,
                workspace_id=model.workspace_id,
                node_type=model.node_type,
                external_id=model.external_id,
                name=model.name,
                details=model.details or {},
                created_at=model.created_at,
            )
            for model in models
        ]

    async def list_edges(self, workspace_id: UUID):
        result = await self._session.execute(
            select(GraphEdgeModel).where(GraphEdgeModel.workspace_id == workspace_id)
        )
        models = result.scalars().all()
        return [
            GraphEdge(
                id=model.id,
                workspace_id=model.workspace_id,
                source_node_id=model.source_node_id,
                target_node_id=model.target_node_id,
                edge_type=model.edge_type,
                details=model.details or {},
                created_at=model.created_at,
            )
            for model in models
        ]
