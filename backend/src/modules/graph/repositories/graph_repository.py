from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class GraphRepository(ABC):
    @abstractmethod
    async def delete_for_workspace(self, workspace_id: UUID | str) -> None:
        ...

    @abstractmethod
    async def create_node(
        self,
        *,
        workspace_id: UUID | str,
        node_type: str,
        external_id: str,
        name: str,
        details: dict[str, Any],
    ):
        ...

    @abstractmethod
    async def create_edge(
        self,
        *,
        workspace_id: UUID | str,
        source_node_id: UUID,
        target_node_id: UUID,
        edge_type: str,
        details: dict[str, Any],
    ):
        ...

    @abstractmethod
    async def list_nodes(self, workspace_id: UUID | str):
        ...

    @abstractmethod
    async def list_edges(self, workspace_id: UUID | str):
        ...
