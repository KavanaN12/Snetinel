import uuid
from datetime import datetime, timezone

import pytest

from src.modules.attack_path.domain.entities import AttackPath
from src.modules.attack_path.services.attack_path_service import AttackPathService
from src.modules.graph.domain.entities import GraphEdge, GraphNode
from src.modules.workspace.domain.entities import Workspace


class FakeGraphRepository:
    def __init__(self, nodes, edges) -> None:
        self._nodes = nodes
        self._edges = edges

    async def list_nodes(self, workspace_id):
        return [node for node in self._nodes if node.workspace_id == workspace_id]

    async def list_edges(self, workspace_id):
        return [edge for edge in self._edges if edge.workspace_id == workspace_id]


class FakeAttackPathRepository:
    def __init__(self) -> None:
        self.paths: list[AttackPath] = []

    async def delete_for_workspace(self, workspace_id):
        self.paths = [path for path in self.paths if path.workspace_id != workspace_id]

    async def create(self, *, workspace_id, attack_type, steps, details):
        path = AttackPath(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            attack_type=attack_type,
            steps=steps,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        self.paths.append(path)
        return path

    async def list_for_workspace(self, workspace_id):
        return [path for path in self.paths if path.workspace_id == workspace_id]


class FakeWorkspaceRepository:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get_by_id(self, workspace_id):
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


@pytest.mark.asyncio
async def test_analyze_builds_attack_paths_from_graph() -> None:
    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Attack Path Workspace",
        description="Attack paths",
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    nodes = [
        GraphNode(id=uuid.uuid4(), workspace_id=workspace.id, node_type="iam_user", external_id="alice", name="alice", details={}),
        GraphNode(id=uuid.uuid4(), workspace_id=workspace.id, node_type="iam_role", external_id="role-1", name="role-1", details={}),
        GraphNode(id=uuid.uuid4(), workspace_id=workspace.id, node_type="iam_policy", external_id="policy-1", name="policy-1", details={}),
        GraphNode(id=uuid.uuid4(), workspace_id=workspace.id, node_type="vpc", external_id="vpc-1", name="vpc-1", details={}),
        GraphNode(id=uuid.uuid4(), workspace_id=workspace.id, node_type="security_group", external_id="sg-1", name="sg-1", details={}),
        GraphNode(id=uuid.uuid4(), workspace_id=workspace.id, node_type="ec2_instance", external_id="instance-1", name="instance-1", details={}),
        GraphNode(id=uuid.uuid4(), workspace_id=workspace.id, node_type="s3_bucket", external_id="bucket-1", name="bucket-1", details={}),
    ]
    edges = [
        GraphEdge(id=uuid.uuid4(), workspace_id=workspace.id, source_node_id=nodes[0].id, target_node_id=nodes[2].id, edge_type="OWNS", details={}),
        GraphEdge(id=uuid.uuid4(), workspace_id=workspace.id, source_node_id=nodes[1].id, target_node_id=nodes[2].id, edge_type="ATTACHED_TO", details={}),
        GraphEdge(id=uuid.uuid4(), workspace_id=workspace.id, source_node_id=nodes[3].id, target_node_id=nodes[4].id, edge_type="CONTAINS", details={}),
        GraphEdge(id=uuid.uuid4(), workspace_id=workspace.id, source_node_id=nodes[4].id, target_node_id=nodes[5].id, edge_type="ATTACHED_TO", details={}),
        GraphEdge(id=uuid.uuid4(), workspace_id=workspace.id, source_node_id=nodes[3].id, target_node_id=nodes[6].id, edge_type="CONNECTED_TO", details={}),
    ]
    attack_repo = FakeAttackPathRepository()
    service = AttackPathService(
        workspace_repository=FakeWorkspaceRepository(workspace),
        graph_repository=FakeGraphRepository(nodes, edges),
        attack_path_repository=attack_repo,
    )

    result = await service.analyze(workspace.id, workspace.owner_id)

    assert result.path_count >= 4
    assert any(path.attack_type == "iam_assume_role" for path in attack_repo.paths)
    assert any(path.attack_type == "iam_policy_attachment" for path in attack_repo.paths)
    assert any(path.attack_type == "s3_access" for path in attack_repo.paths)
    assert any(path.attack_type == "security_group_ec2" for path in attack_repo.paths)
