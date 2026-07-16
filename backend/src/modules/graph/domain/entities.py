from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class GraphNode:
    id: UUID
    workspace_id: UUID
    node_type: str
    external_id: str
    name: str
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class GraphEdge:
    id: UUID
    workspace_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: str
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class GraphBuildResult:
    workspace_id: UUID
    node_count: int
    edge_count: int
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
