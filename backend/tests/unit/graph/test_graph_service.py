import uuid
from datetime import datetime, timezone

import pytest

from src.modules.graph.domain.entities import GraphEdge, GraphNode
from src.modules.graph.services.graph_service import GraphService
from src.modules.workspace.domain.entities import Workspace


class FakeGraphRepository:
    def __init__(self) -> None:
        self.nodes: list[GraphNode] = []
        self.edges: list[GraphEdge] = []

    async def delete_for_workspace(self, workspace_id):
        self.nodes = [node for node in self.nodes if node.workspace_id != workspace_id]
        self.edges = [edge for edge in self.edges if edge.workspace_id != workspace_id]

    async def create_node(self, *, workspace_id, node_type, external_id, name, details):
        node = GraphNode(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            node_type=node_type,
            external_id=external_id,
            name=name,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        self.nodes.append(node)
        return node

    async def create_edge(self, *, workspace_id, source_node_id, target_node_id, edge_type, details):
        edge = GraphEdge(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        self.edges.append(edge)
        return edge

    async def list_nodes(self, workspace_id):
        return [node for node in self.nodes if node.workspace_id == workspace_id]

    async def list_edges(self, workspace_id):
        return [edge for edge in self.edges if edge.workspace_id == workspace_id]


class FakeCloudResourceRepository:
    def __init__(self, resources) -> None:
        self._resources = resources

    async def list_by_workspace(self, workspace_id):
        return [resource for resource in self._resources if resource.workspace_id == workspace_id]


class FakeWorkspaceRepository:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get_by_id(self, workspace_id):
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


@pytest.mark.asyncio
async def test_build_graph_creates_nodes_and_edges_from_resources() -> None:
    owner_id = uuid.uuid4()
    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Graph Workspace",
        description="Graph resources",
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    graph_repo = FakeGraphRepository()
    cloud_resources = [
        type(
            "Resource",
            (),
            {
                "workspace_id": workspace.id,
                "resource_type": "iam_user",
                "resource_id": "alice",
                "name": "alice",
                "details": {"user_id": "u1"},
            },
        )(),
        type(
            "Resource",
            (),
            {
                "workspace_id": workspace.id,
                "resource_type": "iam_policy",
                "resource_id": "policy-1",
                "name": "policy-1",
                "details": {"policy_id": "p1"},
            },
        )(),
        type(
            "Resource",
            (),
            {
                "workspace_id": workspace.id,
                "resource_type": "vpc",
                "resource_id": "vpc-1",
                "name": "vpc-1",
                "details": {"cidr_block": "10.0.0.0/16"},
            },
        )(),
    ]
    service = GraphService(
        workspace_repository=FakeWorkspaceRepository(workspace),
        cloud_resource_repository=FakeCloudResourceRepository(cloud_resources),
        graph_repository=graph_repo,
    )

    response = await service.build_graph(workspace.id, owner_id)

    assert response.node_count == 3
    assert response.edge_count == 1
    assert any(node.node_type == "iam_user" for node in graph_repo.nodes)
    assert any(edge.edge_type == "OWNS" for edge in graph_repo.edges)
