from __future__ import annotations

from collections import deque
from uuid import UUID

from src.modules.attack_path.domain.entities import AttackPath, AttackPathAnalysisResult
from src.modules.attack_path.repositories.attack_path_repository import AttackPathRepository
from src.modules.graph.repositories.graph_repository import GraphRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository


class AttackPathService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        graph_repository: GraphRepository,
        attack_path_repository: AttackPathRepository,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._graph_repository = graph_repository
        self._attack_path_repository = attack_path_repository

    async def analyze(self, workspace_id: UUID | str, current_user_id: UUID | str) -> AttackPathAnalysisResult:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        nodes = await self._graph_repository.list_nodes(workspace_id)
        edges = await self._graph_repository.list_edges(workspace_id)

        await self._attack_path_repository.delete_for_workspace(workspace_id)

        node_lookup = {node.id: node for node in nodes}
        adjacency: dict[UUID, list[tuple[UUID, str]]] = {node.id: [] for node in nodes}
        for edge in edges:
            adjacency.setdefault(edge.source_node_id, []).append((edge.target_node_id, edge.edge_type))
            adjacency.setdefault(edge.target_node_id, []).append((edge.source_node_id, edge.edge_type))

        for node in nodes:
            if node.node_type == "iam_user":
                for target in [candidate for candidate in nodes if candidate.node_type == "iam_role"]:
                    adjacency.setdefault(node.id, []).append((target.id, "ASSUME_ROLE"))

        paths: list[AttackPath] = []
        seen_paths: set[tuple[str, tuple[UUID, ...]]] = set()

        for start_node in nodes:
            queue = deque([(start_node.id, [start_node.id], {start_node.id})])
            while queue:
                current_id, steps, visited = queue.popleft()
                current_node = node_lookup[current_id]
                for neighbor_id, edge_type in adjacency.get(current_id, []):
                    if neighbor_id in visited:
                        continue
                    new_steps = steps + [neighbor_id]
                    if len(new_steps) > 4:
                        continue
                    target_node = node_lookup[neighbor_id]
                    path_type = self._path_type(current_node.node_type, target_node.node_type, edge_type)
                    if path_type and (path_type, tuple(new_steps)) not in seen_paths:
                        seen_paths.add((path_type, tuple(new_steps)))
                        path = await self._attack_path_repository.create(
                            workspace_id=workspace.id,
                            attack_type=path_type,
                            steps=[self._serialize_node(node_lookup[node_id]) for node_id in new_steps],
                            details={"edge_type": edge_type},
                        )
                        paths.append(path)
                    if len(new_steps) < 4:
                        queue.append((neighbor_id, new_steps, visited | {neighbor_id}))

        return AttackPathAnalysisResult(workspace_id=workspace.id, path_count=len(paths), paths=paths)

    async def list_paths(self, workspace_id: UUID | str, current_user_id: UUID | str) -> AttackPathAnalysisResult:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        paths = await self._attack_path_repository.list_for_workspace(workspace_id)
        return AttackPathAnalysisResult(workspace_id=workspace.id, path_count=len(paths), paths=paths)

    @staticmethod
    def _path_type(source_type: str, target_type: str, edge_type: str) -> str | None:
        if source_type == "iam_user" and target_type == "iam_role" and edge_type == "ASSUME_ROLE":
            return "iam_assume_role"
        if source_type in {"iam_user", "iam_role"} and target_type == "iam_policy" and edge_type in {"OWNS", "ATTACHED_TO"}:
            return "iam_policy_attachment"
        if source_type == "vpc" and target_type == "s3_bucket" and edge_type == "CONNECTED_TO":
            return "s3_access"
        if source_type == "vpc" and target_type == "security_group" and edge_type == "CONTAINS":
            return "security_group_ec2"
        if source_type == "security_group" and target_type == "ec2_instance" and edge_type == "ATTACHED_TO":
            return "security_group_ec2"
        return None

    @staticmethod
    def _serialize_node(node) -> dict:
        return {
            "id": str(node.id),
            "node_type": node.node_type,
            "external_id": node.external_id,
            "name": node.name,
        }
