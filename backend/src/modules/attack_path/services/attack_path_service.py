from __future__ import annotations

from uuid import UUID

from src.modules.attack_path.domain.entities import AttackPath, AttackPathAnalysisResult
from src.modules.attack_path.graph_algorithms import DirectedGraphAnalysis, WeightedEdge
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
        adjacency: dict[UUID, list[WeightedEdge]] = {node.id: [] for node in nodes}
        edge_lookup: dict[tuple[UUID, UUID], list] = {}
        traversable_edges = {"ASSUME_ROLE", "PASS_ROLE", "CAN_ACCESS"}
        for edge in edges:
            if edge.edge_type not in traversable_edges:
                continue
            effort = edge.details.get("effort_cost", 1.0)
            adjacency.setdefault(edge.source_node_id, []).append(
                WeightedEdge(edge.target_node_id, max(float(effort), 0.0))
            )
            edge_lookup.setdefault((edge.source_node_id, edge.target_node_id), []).append(edge)

        paths: list[AttackPath] = []
        sources = {
            node.id for node in nodes if node.node_type in {"iam_user", "iam_role"}
        }
        targets = {
            node.id
            for node in nodes
            if node.node_type in {"iam_role", "s3_bucket", "ec2_instance", "kms_key", "lambda_function"}
            and (
                node.node_type != "iam_role"
                or any(
                    edge.source_node_id == node.id
                    and edge.edge_type == "ATTACHED_TO"
                    and edge.details.get("privileged")
                    for edge in edges
                )
            )
        }
        analysis = DirectedGraphAnalysis(adjacency)
        choke_points = analysis.choke_points(sources, targets)
        components = analysis.strongly_connected_components()
        component_by_node = {
            node_id: component_index
            for component_index, component in enumerate(components)
            for node_id in component
        }

        for source_id in sorted(sources, key=str):
            for target_id in sorted(targets - {source_id}, key=str):
                breadth_path = analysis.breadth_first_path(source_id, target_id)
                if breadth_path is None or len(breadth_path) < 2:
                    continue
                depth_path = analysis.depth_first_path(source_id, target_id)
                weighted_path = analysis.dijkstra_path(source_id, target_id)
                if weighted_path is None:
                    continue
                selected_path = weighted_path[0]
                target_node = node_lookup[target_id]
                attack_type = self._target_attack_type(target_node.node_type)
                if attack_type is None:
                    continue
                path_edges = [
                    edge
                    for source, target in zip(selected_path, selected_path[1:])
                    for edge in edge_lookup.get((source, target), [])
                ]
                path = await self._attack_path_repository.create(
                    workspace_id=workspace.id,
                    attack_type=attack_type,
                    steps=[self._serialize_node(node_lookup[node_id]) for node_id in selected_path],
                    details={
                        "algorithms": {
                            "bfs": [str(node_id) for node_id in breadth_path],
                            "dfs": [str(node_id) for node_id in depth_path or []],
                            "dijkstra": [str(node_id) for node_id in selected_path],
                            "effort_cost": weighted_path[1],
                        },
                        "edge_evidence": [
                            {
                                "source": str(edge.source_node_id),
                                "target": str(edge.target_node_id),
                                "type": edge.edge_type,
                                "details": edge.details,
                            }
                            for edge in path_edges
                        ],
                        "blast_radius": len(analysis.blast_radius(source_id)) - 1,
                        "choke_points": [str(node_id) for node_id in sorted(choke_points, key=str)],
                        "strongly_connected_component": component_by_node.get(source_id),
                    },
                )
                paths.append(path)

        return AttackPathAnalysisResult(workspace_id=workspace.id, path_count=len(paths), paths=paths)

    async def list_paths(self, workspace_id: UUID | str, current_user_id: UUID | str) -> AttackPathAnalysisResult:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        paths = await self._attack_path_repository.list_for_workspace(workspace_id)
        return AttackPathAnalysisResult(workspace_id=workspace.id, path_count=len(paths), paths=paths)

    @staticmethod
    def _target_attack_type(target_type: str) -> str | None:
        if target_type == "iam_role":
            return "iam_assume_role"
        resource_types = {
            "s3_bucket": "s3_access",
            "ec2_instance": "ec2_access",
            "kms_key": "kms_access",
            "lambda_function": "lambda_access",
        }
        return resource_types.get(target_type)

    @staticmethod
    def _serialize_node(node) -> dict:
        return {
            "id": str(node.id),
            "node_type": node.node_type,
            "external_id": node.external_id,
            "name": node.name,
        }
