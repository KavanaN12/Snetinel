from __future__ import annotations

from uuid import UUID

from src.modules.attack_path.repositories.attack_path_repository import AttackPathRepository
from src.modules.discovery.repositories.cloud_resource_repository import CloudResourceRepository
from src.modules.risk_scoring.repositories.finding_repository import FindingRepository
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository


class DashboardService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        finding_repository: FindingRepository,
        cloud_resource_repository: CloudResourceRepository,
        attack_path_repository: AttackPathRepository,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._finding_repository = finding_repository
        self._cloud_resource_repository = cloud_resource_repository
        self._attack_path_repository = attack_path_repository

    async def get_summary(self, workspace_id: UUID | str, current_user_id: UUID | str) -> dict[str, object]:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if not workspace or str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceNotFoundError("Workspace not found")

        findings = await self._finding_repository.list_for_workspace(workspace_id)
        resources = await self._cloud_resource_repository.list_by_workspace(workspace_id)
        attack_paths = await self._attack_path_repository.list_for_workspace(workspace_id)

        severity_counts: dict[str, int] = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        finding_counts = {
            "total": len(findings),
            "open": sum(1 for finding in findings if finding.status == "open"),
            "resolved": sum(1 for finding in findings if finding.status == "resolved"),
            "stale": sum(1 for finding in findings if finding.status == "stale"),
        }

        return {
            "severity_counts": severity_counts,
            "finding_counts": finding_counts,
            "resource_counts": {"total": len(resources)},
            "attack_path_counts": {"total": len(attack_paths)},
        }
