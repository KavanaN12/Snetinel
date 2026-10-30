from __future__ import annotations

from uuid import UUID

from src.modules.graph.domain.entities import GraphBuildResult, GraphEdge, GraphNode
from src.modules.graph.repositories.graph_repository import GraphRepository
from src.modules.iam_analysis.policy_evaluator import IamPolicyEvaluator
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
            details = dict(resource.details or {})
            resource_arn = getattr(resource, "arn", None)
            if resource_arn:
                details.setdefault("arn", resource_arn)
            node = await self._graph_repository.create_node(
                workspace_id=workspace_id,
                node_type=node_type,
                external_id=resource.resource_id,
                name=resource.name or resource.resource_id,
                details=details,
            )
            node_lookup[resource_key] = node
            nodes.append(node)

        for resource in resources:
            owner_node = node_lookup.get((resource.resource_type, resource.resource_id))
            if owner_node is None:
                continue
            for inline_policy in (resource.details or {}).get("inline_policies", []):
                if not isinstance(inline_policy, dict) or not inline_policy.get("document"):
                    continue
                policy_name = str(inline_policy.get("name") or "unnamed")
                policy_node = await self._graph_repository.create_node(
                    workspace_id=workspace_id,
                    node_type="iam_policy",
                    external_id=f"{resource.resource_type}:{resource.resource_id}:{policy_name}",
                    name=policy_name,
                    details={
                        "document": inline_policy["document"],
                        "policy_type": "inline",
                        "attachment_principal_type": owner_node.node_type,
                        "attachment_principal": owner_node.external_id,
                        "actions": self._normalize_policy_actions(inline_policy["document"]),
                    },
                )
                nodes.append(policy_node)
                node_lookup[("iam_policy_inline", policy_node.external_id)] = policy_node

        edges: list[GraphEdge] = []
        seen_edges: set[tuple[UUID, UUID, str]] = set()

        async def add_edge(source_node: GraphNode, target_node: GraphNode, edge_type: str, details: dict) -> None:
            edge_key = (source_node.id, target_node.id, edge_type)
            if edge_key in seen_edges:
                return
            seen_edges.add(edge_key)
            created_edge = await self._graph_repository.create_edge(
                workspace_id=workspace_id,
                source_node_id=source_node.id,
                target_node_id=target_node.id,
                edge_type=edge_type,
                details=details,
            )
            edges.append(created_edge)

        policies_by_arn = {
            str((node.details or {}).get("policy_arn") or (node.details or {}).get("arn")): node
            for node in nodes
            if node.node_type == "iam_policy"
            and ((node.details or {}).get("policy_arn") or (node.details or {}).get("arn"))
        }
        principals_by_name = {
            (node.node_type, node.external_id): node
            for node in nodes
            if node.node_type in {"iam_user", "iam_role", "iam_group"}
        }

        for node in list(principals_by_name.values()):
            details = node.details or {}
            for policy_arn in details.get("attached_policy_arns", []):
                policy_node = policies_by_arn.get(str(policy_arn))
                if policy_node is not None:
                    await add_edge(
                        node,
                        policy_node,
                        "ATTACHED_TO",
                        {
                            "kind": "managed-policy-assignment",
                            "privileged": self._is_privileged_policy(policy_node),
                        },
                    )

        for group_node in [
            node for node in nodes if node.node_type == "iam_group"
        ]:
            for user_name in (group_node.details or {}).get("member_user_names", []):
                user_node = principals_by_name.get(("iam_user", str(user_name)))
                if user_node is not None:
                    await add_edge(user_node, group_node, "MEMBER_OF", {"kind": "iam-group-membership"})

        for policy_node in nodes:
            if policy_node.node_type != "iam_policy" or not (policy_node.details or {}).get("policy_type") == "inline":
                continue
            owner = principals_by_name.get(
                (
                    str((policy_node.details or {}).get("attachment_principal_type")),
                    str((policy_node.details or {}).get("attachment_principal")),
                )
            )
            if owner is not None:
                await add_edge(owner, policy_node, "ATTACHED_TO", {"kind": "inline-policy-assignment"})

        evaluator = IamPolicyEvaluator()
        for source_node in list(principals_by_name.values()):
            if source_node.node_type not in {"iam_user", "iam_role"}:
                continue
            source_arn = (source_node.details or {}).get("arn")
            if not source_arn:
                continue
            identity_policies = self._effective_identity_policies(
                source_node,
                principals_by_name,
                policies_by_arn,
            )
            boundary_policies = self._permission_boundary(source_node, policies_by_arn)
            for role_node in [node for node in nodes if node.node_type == "iam_role"]:
                if role_node.id == source_node.id:
                    continue
                target_details = role_node.details or {}
                role_arn = target_details.get("arn")
                trust_policy = target_details.get("trust_policy")
                if not role_arn or not isinstance(trust_policy, (dict, str)):
                    continue
                pass_role_result = evaluator.evaluate(
                    action="iam:PassRole",
                    resource=str(role_arn),
                    policies=identity_policies,
                    permission_boundaries=boundary_policies,
                )
                can_create_and_invoke_lambda = all(
                    evaluator.evaluate(
                        action=action,
                        resource="*",
                        policies=identity_policies,
                        permission_boundaries=boundary_policies,
                    ).allowed
                    for action in ("lambda:CreateFunction", "lambda:InvokeFunction")
                )
                if pass_role_result.allowed and can_create_and_invoke_lambda:
                    await add_edge(
                        source_node,
                        role_node,
                        "PASS_ROLE",
                        {
                            "kind": "effective-iam-permission",
                            "permission_statements": list(pass_role_result.matched_allow_statements),
                            "execution_actions": [
                                "lambda:CreateFunction",
                                "lambda:InvokeFunction",
                            ],
                            "cross_account": self._account_id(str(source_arn))
                            != self._account_id(str(role_arn)),
                        },
                    )
                trust_result = evaluator.evaluate_trust(
                    trust_policy=trust_policy,
                    principal=str(source_arn),
                )
                permission_result = evaluator.evaluate(
                    action="sts:AssumeRole",
                    resource=str(role_arn),
                    policies=identity_policies,
                    permission_boundaries=boundary_policies,
                )
                if not permission_result.allowed:
                    continue
                if trust_result.allowed:
                    await add_edge(
                        source_node,
                        role_node,
                        "ASSUME_ROLE",
                        {
                            "kind": "effective-iam-permission",
                            "trust_statements": list(trust_result.matched_allow_statements),
                            "permission_statements": list(permission_result.matched_allow_statements),
                            "cross_account": self._account_id(str(source_arn))
                            != self._account_id(str(role_arn)),
                        },
                    )
                elif trust_result.missing_context_keys or trust_result.unsupported_conditions:
                    await add_edge(
                        source_node,
                        role_node,
                        "POTENTIAL_ASSUME_ROLE",
                        {
                            "kind": "conditioned-trust-policy",
                            "decision": trust_result.decision,
                            "missing_context_keys": list(trust_result.missing_context_keys),
                            "unsupported_conditions": list(trust_result.unsupported_conditions),
                        },
                    )
            for resource_node in nodes:
                probes = self._resource_permission_probes(resource_node)
                if not probes:
                    continue
                allowed_actions = []
                evidence: dict[str, list[str]] = {}
                resource_arns: dict[str, str] = {}
                potential_permissions = {}
                for resource_action, resource_arn in probes:
                    resource_details = resource_node.details or {}
                    resource_policy_document = resource_details.get(
                        "resource_policy"
                    ) or resource_details.get("key_policy")
                    resource_policies = (
                        [resource_policy_document]
                        if resource_policy_document is not None
                        else None
                    )
                    resource_account = resource_details.get("account_id") or self._account_id(
                        str((resource_details.get("arn") or ""))
                    )
                    source_account = self._account_id(str(source_arn))
                    cross_account = (
                        source_account != str(resource_account)
                        if source_account and resource_account
                        else None
                    )
                    evaluation = evaluator.evaluate(
                        action=resource_action,
                        resource=resource_arn,
                        policies=identity_policies,
                        permission_boundaries=boundary_policies,
                        resource_policies=resource_policies,
                        principal_arn=str(source_arn),
                        cross_account=cross_account,
                    )
                    if evaluation.allowed:
                        allowed_actions.append(resource_action)
                        evidence[resource_action] = list(evaluation.matched_allow_statements)
                        resource_arns[resource_action] = resource_arn
                    else:
                        if evaluation.missing_context_keys or evaluation.unsupported_conditions:
                            potential_permissions[resource_action] = {
                                "missing_context_keys": list(evaluation.missing_context_keys),
                                "unsupported_conditions": list(evaluation.unsupported_conditions),
                                "resource_arn": resource_arn,
                            }
                        elif evaluation.missing_evidence:
                            potential_permissions[resource_action] = {
                                "missing_evidence": list(evaluation.missing_evidence),
                                "resource_arn": resource_arn,
                            }
                if allowed_actions:
                    await add_edge(
                        source_node,
                        resource_node,
                        "CAN_ACCESS",
                        {
                            "kind": "effective-iam-permission",
                            "actions": sorted(set(allowed_actions)),
                            "policy_statements": evidence,
                            "resource_arns": resource_arns,
                        },
                    )
                if potential_permissions:
                    await add_edge(
                        source_node,
                        resource_node,
                        "POTENTIAL_ACCESS",
                        {
                            "kind": "conditional-or-unsupported-policy",
                            "permissions": potential_permissions,
                        },
                    )

        for node in nodes:
            if node.node_type == "vpc":
                for security_group in [candidate for candidate in nodes if candidate.node_type == "security_group"]:
                    if (security_group.details or {}).get("vpc_id") == node.external_id:
                        await add_edge(node, security_group, "CONTAINS", {"kind": "networking"})
            if node.node_type == "security_group":
                for instance in [candidate for candidate in nodes if candidate.node_type == "ec2_instance"]:
                    security_group_ids = (instance.details or {}).get("security_group_ids", [])
                    if node.external_id in security_group_ids:
                        await add_edge(node, instance, "ATTACHED_TO", {"kind": "networking"})

        return GraphBuildResult(
            workspace_id=workspace_id,
            node_count=len(nodes),
            edge_count=len(edges),
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def _effective_identity_policies(
        identity_node: GraphNode,
        principals_by_name: dict[tuple[str, str], GraphNode],
        policies_by_arn: dict[str, GraphNode],
    ) -> list[dict]:
        principal_nodes = [identity_node]
        if identity_node.node_type == "iam_user":
            principal_nodes.extend(
                principals_by_name[("iam_group", str(group_name))]
                for group_name in (identity_node.details or {}).get("group_names", [])
                if ("iam_group", str(group_name)) in principals_by_name
            )

        policy_documents: list[dict] = []
        seen_documents: set[str] = set()
        for principal_node in principal_nodes:
            details = principal_node.details or {}
            for policy_arn in details.get("attached_policy_arns", []):
                policy_node = policies_by_arn.get(str(policy_arn))
                document = (policy_node.details or {}).get("document") if policy_node else None
                if document is not None and str(policy_arn) not in seen_documents:
                    policy_documents.append(document)
                    seen_documents.add(str(policy_arn))
            for policy in details.get("inline_policies", []):
                if isinstance(policy, dict) and policy.get("document") is not None:
                    policy_documents.append(policy["document"])
            for candidate in policies_by_arn.values():
                candidate_details = candidate.details or {}
                if (
                    candidate_details.get("policy_type") == "inline"
                    and candidate_details.get("attachment_principal_type") == principal_node.node_type
                    and candidate_details.get("attachment_principal") == principal_node.external_id
                ):
                    policy_documents.append(candidate_details["document"])
        return policy_documents

    @staticmethod
    def _account_id(arn: str) -> str | None:
        parts = arn.split(":")
        return parts[4] if len(parts) > 4 else None

    @staticmethod
    def _permission_boundary(
        identity_node: GraphNode,
        policies_by_arn: dict[str, GraphNode],
    ) -> list[dict] | None:
        boundary_arn = (identity_node.details or {}).get("permissions_boundary_arn")
        if not boundary_arn:
            return None
        boundary_node = policies_by_arn.get(str(boundary_arn))
        if boundary_node is None:
            return []
        document = (boundary_node.details or {}).get("document")
        return [document] if document is not None else []

    @staticmethod
    def _resource_permission_probes(node: GraphNode) -> list[tuple[str, str]]:
        arn = (node.details or {}).get("arn")
        if not arn:
            return []
        if node.node_type == "s3_bucket":
            object_arn = f"{arn.rstrip('/')}/*"
            return [
                ("s3:ListBucket", str(arn)),
                ("s3:GetObject", object_arn),
                ("s3:PutObject", object_arn),
                ("s3:DeleteObject", object_arn),
            ]
        if node.node_type == "ec2_instance":
            return [
                ("ec2:StartInstances", str(arn)),
                ("ec2:StopInstances", str(arn)),
                ("ec2:TerminateInstances", str(arn)),
            ]
        if node.node_type == "kms_key":
            return [
                ("kms:Decrypt", str(arn)),
                ("kms:Encrypt", str(arn)),
                ("kms:PutKeyPolicy", str(arn)),
                ("kms:ScheduleKeyDeletion", str(arn)),
            ]
        if node.node_type == "lambda_function":
            return [
                ("lambda:InvokeFunction", str(arn)),
                ("lambda:UpdateFunctionCode", str(arn)),
                ("lambda:UpdateFunctionConfiguration", str(arn)),
                ("lambda:AddPermission", str(arn)),
            ]
        return []

    @staticmethod
    def _is_privileged_policy(policy_node: GraphNode) -> bool:
        details = policy_node.details or {}
        document = IamPolicyEvaluator.parse_document(details.get("document"))
        if document is None:
            return False
        statement = document.get("Statement")
        statements = statement if isinstance(statement, list) else [statement] if statement else []
        sensitive_actions = {
            "iam:PassRole",
            "iam:AttachRolePolicy",
            "iam:PutRolePolicy",
            "iam:CreatePolicyVersion",
            "iam:UpdateAssumeRolePolicy",
            "iam:CreateAccessKey",
            "iam:CreateLoginProfile",
            "sts:AssumeRole",
        }
        evaluator = IamPolicyEvaluator()
        for item in statements:
            if not isinstance(item, dict) or item.get("Effect") != "Allow":
                continue
            resources = item.get("Resource", ["*"])
            if isinstance(resources, str):
                resources = [resources]
            if not isinstance(resources, list) or not resources:
                resources = ["*"]
            for action in sensitive_actions:
                for resource in resources:
                    if not isinstance(resource, str):
                        continue
                    result = evaluator.evaluate(
                        action=action,
                        resource=resource,
                        policies=[document],
                    )
                    if result.allowed:
                        return True
        return False

    @staticmethod
    def _normalize_policy_actions(policy_document) -> list[str]:
        policy_document = IamPolicyEvaluator.parse_document(policy_document)
        if policy_document is None:
            return []
        statement = policy_document.get("Statement")
        statements = statement if isinstance(statement, list) else [statement] if statement else []
        actions: list[str] = []
        for item in statements:
            if not isinstance(item, dict):
                continue
            action = item.get("Action")
            if isinstance(action, list):
                actions.extend(str(value) for value in action)
            elif action is not None:
                actions.append(str(action))
        return sorted(set(actions))

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
            "iam_group": "iam_group",
            "iam_policy": "iam_policy",
            "s3_bucket": "s3_bucket",
            "ec2_instance": "ec2_instance",
            "security_group": "security_group",
            "vpc": "vpc",
            "kms_key": "kms_key",
            "lambda_function": "lambda_function",
        }
        return mapping.get(resource_type)
