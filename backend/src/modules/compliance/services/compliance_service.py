from __future__ import annotations

from uuid import UUID

from src.modules.compliance.domain.entities import ComplianceFinding, ComplianceSummary
from src.modules.compliance.repositories.compliance_repository import ComplianceRepository
from src.modules.discovery.repositories.cloud_resource_repository import CloudResourceRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository


class ComplianceService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        cloud_resource_repository: CloudResourceRepository,
        compliance_repository: ComplianceRepository,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._cloud_resource_repository = cloud_resource_repository
        self._compliance_repository = compliance_repository

    async def evaluate_workspace(self, workspace_id: UUID | str, current_user_id: UUID | str) -> dict[str, object]:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        resources = await self._cloud_resource_repository.list_by_workspace(workspace_id)
        findings: list[ComplianceFinding] = []

        for resource in resources:
            if resource.resource_type == "ec2" and getattr(resource, "details", {}).get("public"):
                finding = await self._compliance_repository.create_result(
                    workspace_id=workspace.id,
                    check_id="cis-aws-2.1",
                    title="Public EC2 instance",
                    description="EC2 instance is exposed publicly.",
                    severity="high",
                    status="failed",
                    remediation="Restrict ingress to approved IP ranges.",
                    framework="cis-aws",
                    details={"resource_id": resource.resource_id},
                )
                findings.append(self._coerce_finding(finding))

        summary = ComplianceSummary(
            total_checks=max(1, len(findings) or 1),
            passed_checks=0,
            failed_checks=len(findings),
            warning_checks=0,
        )
        return {
            "workspace_id": workspace.id,
            "summary": {
                "total_checks": summary.total_checks,
                "passed_checks": summary.passed_checks,
                "failed_checks": summary.failed_checks,
                "warning_checks": summary.warning_checks,
            },
            "findings": findings,
        }

    def _coerce_finding(self, finding: object) -> ComplianceFinding:
        if isinstance(finding, ComplianceFinding):
            return finding
        if isinstance(finding, dict):
            return ComplianceFinding(
                id=finding.get("id"),
                workspace_id=finding.get("workspace_id"),
                check_id=finding.get("check_id", ""),
                title=finding.get("title", ""),
                description=finding.get("description", ""),
                severity=finding.get("severity", "low"),
                status=finding.get("status", "failed"),
                remediation=finding.get("remediation", ""),
                framework=finding.get("framework", "cis-aws"),
                details=finding.get("details") or {},
                created_at=finding.get("created_at"),
            )
        return ComplianceFinding(
            id=getattr(finding, "id", None),
            workspace_id=getattr(finding, "workspace_id", None),
            check_id=getattr(finding, "check_id", ""),
            title=getattr(finding, "title", ""),
            description=getattr(finding, "description", ""),
            severity=getattr(finding, "severity", "low"),
            status=getattr(finding, "status", "failed"),
            remediation=getattr(finding, "remediation", ""),
            framework=getattr(finding, "framework", "cis-aws"),
            details=getattr(finding, "details", {}) or {},
            created_at=getattr(finding, "created_at", None),
        )
