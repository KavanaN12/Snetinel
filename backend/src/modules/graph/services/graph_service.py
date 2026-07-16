from __future__ import annotations

from uuid import UUID

from src.modules.graph.domain.entities import GraphBuildResult, GraphEdge, GraphNode
from src.modules.graph.repositories.graph_repository import GraphRepository
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository
from src.modules.discovery.repositories.cloud_resource_repository import CloudResourceRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError


class GraphService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        cloud_resource_repository: CloudResourceRepository,
        graph_repository: GraphRepository,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._cloud_resource_repository = cloud_resource_repository
        self._graph_repository = graph_repository

    async def build_graph(self, workspace_id: UUID | str, current_user_id: UUID | str) -> GraphBuildResult:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        await self._graph_repository.delete_for_workspace(workspace_id)

        resources = await self._cloud_resource_repository.list_by_workspace(workspace_id)
        nodes: list[GraphNode] = []
        node_lookup: dict[tuple[str, str], GraphNode] = {}

        for resource in resources:
            node_type = self._map_resource_type(resource.resource_type)
            if not node_type:
                continue
            resource_key = (resource.resource_type, resource.resource_id)
            if resource_key in node_lookup:
                continue
            node = await self._graph_repository.create_node(
                workspace_id=workspace_id,
                node_type=node_type,
                external_id=resource.resource_id,
                name=resource.name or resource.resource_id,
                details=resource.details or {},
            )
            node_lookup[resource_key] = node
            nodes.append(node)

        edges: list[GraphEdge] = []
        for node in nodes:
            if node.node_type == "iam_user":
                for policy in [candidate for candidate in nodes if candidate.node_type == "iam_policy"]:
                    edges.append(
                        await self._graph_repository.create_edge(
                            workspace_id=workspace_id,
                            source_node_id=node.id,
                            target_node_id=policy.id,
                            edge_type="OWNS",
                            details={"kind": "policy-assignment"},
                        )
                    )
            if node.node_type == "iam_role":
                for policy in [candidate for candidate in nodes if candidate.node_type == "iam_policy"]:
                    edges.append(
                        await self._graph_repository.create_edge(
                            workspace_id=workspace_id,
                            source_node_id=node.id,
                            target_node_id=policy.id,
                            edge_type="ATTACHED_TO",
                            details={"kind": "policy-assignment"},
                        )
                    )
            if node.node_type == "vpc":
                for security_group in [candidate for candidate in nodes if candidate.node_type == "security_group"]:
                    edges.append(
                        await self._graph_repository.create_edge(
                            workspace_id=workspace_id,
                            source_node_id=node.id,
                            target_node_id=security_group.id,
                            edge_type="CONTAINS",
                            details={"kind": "networking"},
                        )
                    )
            if node.node_type == "security_group":
                for instance in [candidate for candidate in nodes if candidate.node_type == "ec2_instance"]:
                    edges.append(
                        await self._graph_repository.create_edge(
                            workspace_id=workspace_id,
                            source_node_id=node.id,
                            target_node_id=instance.id,
                            edge_type="ATTACHED_TO",
                            details={"kind": "networking"},
                        )
                    )
            if node.node_type == "vpc":
                for bucket in [candidate for candidate in nodes if candidate.node_type == "s3_bucket"]:
                    edges.append(
                        await self._graph_repository.create_edge(
                            workspace_id=workspace_id,
                            source_node_id=node.id,
                            target_node_id=bucket.id,
                            edge_type="CONNECTED_TO",
                            details={"kind": "networking"},
                        )
                    )

        return GraphBuildResult(
            workspace_id=workspace_id,
            node_count=len(nodes),
            edge_count=len(edges),
            nodes=nodes,
            edges=edges,
        )

    async def list_graph(self, workspace_id: UUID | str, current_user_id: UUID | str) -> GraphBuildResult:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        nodes = await self._graph_repository.list_nodes(workspace_id)
        edges = await self._graph_repository.list_edges(workspace_id)
        return GraphBuildResult(
            workspace_id=workspace_id,
            node_count=len(nodes),
            edge_count=len(edges),
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def _map_resource_type(resource_type: str) -> str | None:
        mapping = {
            "iam_user": "iam_user",
            "iam_role": "iam_role",
            "iam_policy": "iam_policy",
            "s3_bucket": "s3_bucket",
            "ec2_instance": "ec2_instance",
            "security_group": "security_group",
            "vpc": "vpc",
        }
        return mapping.get(resource_type)
