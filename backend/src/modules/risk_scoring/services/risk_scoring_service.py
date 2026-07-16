from __future__ import annotations

from uuid import UUID, uuid4

from src.modules.attack_path.repositories.attack_path_repository import AttackPathRepository
from src.modules.risk_scoring.domain.entities import Finding, FindingEvaluationResult
from src.modules.risk_scoring.repositories.finding_repository import FindingRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository


class RiskScoringService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        attack_path_repository: AttackPathRepository,
        finding_repository: FindingRepository,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._attack_path_repository = attack_path_repository
        self._finding_repository = finding_repository

    async def generate_findings(self, workspace_id: UUID | str, current_user_id: UUID | str) -> FindingEvaluationResult:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        if self._finding_repository is not None:
            await self._finding_repository.delete_for_workspace(workspace_id)

        attack_paths = await self._attack_path_repository.list_for_workspace(workspace_id)
        findings: list[Finding] = []
        for attack_path in attack_paths:
            severity = self._severity_for(attack_path.attack_type)
            title, description = self._build_finding_details(attack_path)
            if self._finding_repository is None:
                findings.append(
                    self._build_finding(
                        workspace_id=workspace.id,
                        title=title,
                        description=description,
                        severity=severity,
                        status="open",
                        evidence_subgraph={
                            "attack_type": attack_path.attack_type,
                            "steps": attack_path.steps,
                            "edge_type": getattr(attack_path.details, "get", lambda *_: None)("edge_type"),
                        },
                        affected_resource_ids=[step.get("id") for step in attack_path.steps if step.get("id")],
                    )
                )
            else:
                findings.append(
                    await self._finding_repository.create(
                        workspace_id=workspace.id,
                        title=title,
                        description=description,
                        severity=severity,
                        status="open",
                        evidence_subgraph={
                            "attack_type": attack_path.attack_type,
                            "steps": attack_path.steps,
                            "edge_type": attack_path.details.get("edge_type"),
                        },
                        affected_resource_ids=[step.get("id") for step in attack_path.steps if step.get("id")],
                    )
                )

        return FindingEvaluationResult(workspace_id=workspace.id, finding_count=len(findings), findings=findings)

    async def list_findings(self, workspace_id: UUID | str, current_user_id: UUID | str) -> FindingEvaluationResult:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        if self._finding_repository is None:
            return FindingEvaluationResult(workspace_id=workspace.id, finding_count=0, findings=[])

        findings = await self._finding_repository.list_for_workspace(workspace_id)
        return FindingEvaluationResult(workspace_id=workspace.id, finding_count=len(findings), findings=findings)

    @staticmethod
    def _severity_for(attack_type: str) -> str:
        mapping = {
            "iam_assume_role": "high",
            "iam_policy_attachment": "medium",
            "s3_access": "high",
            "security_group_ec2": "medium",
        }
        return mapping.get(attack_type, "low")

    @staticmethod
    def _build_finding(
        *,
        workspace_id: UUID | str,
        title: str,
        description: str,
        severity: str,
        status: str,
        evidence_subgraph: dict,
        affected_resource_ids: list[str],
    ) -> Finding:
        return Finding(
            id=uuid4(),
            workspace_id=RiskScoringService._coerce_uuid(workspace_id),
            title=title,
            description=description,
            severity=severity,
            status=status,
            evidence_subgraph=evidence_subgraph,
            affected_resource_ids=affected_resource_ids,
        )

    @staticmethod
    def _build_finding_details(attack_path) -> tuple[str, str]:
        attack_type = attack_path.attack_type
        title = {
            "iam_assume_role": "Privileged IAM role assumption path",
            "iam_policy_attachment": "IAM policy attachment path",
            "s3_access": "S3 access exposure path",
            "security_group_ec2": "Security group to EC2 exposure path",
        }.get(attack_type, "Persisted attack path")
        description = (
            f"A persisted attack path of type {attack_type} was detected from the current graph. "
            f"The evidence subgraph contains {len(attack_path.steps)} steps."
        )
        return title, description

    @staticmethod
    def _coerce_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except ValueError:
            return uuid4()
