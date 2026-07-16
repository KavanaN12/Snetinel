from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GraphNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    node_type: str
    external_id: str
    name: str
    details: dict[str, Any]


class GraphEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: str
    details: dict[str, Any]


class GraphResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    node_count: int
    edge_count: int
    nodes: list[GraphNodeResponse] = []
    edges: list[GraphEdgeResponse] = []
