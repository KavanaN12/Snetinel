from types import SimpleNamespace
from uuid import UUID

import pytest

from src.modules.compliance.controllers.compliance_controller import get_compliance_service
from src.modules.compliance.schemas.responses import ComplianceEvaluationResponse
from src.modules.compliance.repositories.postgres_compliance_repository import PostgresComplianceRepository
from src.modules.compliance.services.compliance_service import ComplianceService
from src.modules.discovery.repositories.postgres_cloud_resource_repository import PostgresCloudResourceRepository
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository


class StubWorkspaceRepository:
    def __init__(self, workspace):
        self._workspace = workspace

    async def get_by_id(self, workspace_id):
        return self._workspace


class StubCloudResourceRepository:
    def __init__(self, resources):
        self._resources = resources

    async def list_by_workspace(self, workspace_id):
        return self._resources


class StubComplianceRepository:
    def __init__(self):
        self.items = []

    async def create_result(self, **kwargs):
        self.items.append(kwargs)
        return kwargs

    async def list_for_workspace(self, workspace_id):
        return [item for item in self.items if item["workspace_id"] == workspace_id]


@pytest.mark.asyncio
async def test_evaluate_workspace_creates_cis_findings():
    workspace = SimpleNamespace(id="workspace-1", owner_id="user-1")
    resources = [
        SimpleNamespace(
            resource_type="ec2",
            resource_id="i-123",
            name="public-host",
            details={"public": True},
        )
    ]

    service = ComplianceService(
        workspace_repository=StubWorkspaceRepository(workspace),
        cloud_resource_repository=StubCloudResourceRepository(resources),
        compliance_repository=StubComplianceRepository(),
    )

    result = await service.evaluate_workspace("workspace-1", "user-1")

    assert result["summary"]["total_checks"] == 1
    assert result["summary"]["failed_checks"] == 1
    assert result["findings"][0].check_id == "cis-aws-2.1"
    assert result["findings"][0].status == "failed"


def test_compliance_evaluation_response_serializes_uuid_values():
    workspace_id = UUID("12345678-1234-5678-1234-567812345678")
    finding_id = UUID("87654321-4321-8765-4321-876543214321")

    response = ComplianceEvaluationResponse(
        workspace_id=workspace_id,
        summary={"total_checks": 1, "passed_checks": 0, "failed_checks": 1, "warning_checks": 0},
        findings=[
            {
                "id": finding_id,
                "workspace_id": workspace_id,
                "check_id": "cis-aws-2.1",
                "title": "Public EC2 instance",
                "description": "EC2 instance is exposed publicly.",
                "severity": "high",
                "status": "failed",
                "remediation": "Restrict ingress to approved IP ranges.",
                "framework": "cis-aws",
                "details": {"resource_id": "i-123"},
            }
        ],
    )

    serialized = response.model_dump(mode="json")

    assert serialized["workspace_id"] == str(workspace_id)
    assert serialized["findings"][0]["workspace_id"] == str(workspace_id)
    assert serialized["findings"][0]["id"] == str(finding_id)


def test_get_compliance_service_wires_repositories():
    session = object()

    service = get_compliance_service(session)

    assert isinstance(service._workspace_repository, PostgresWorkspaceRepository)
    assert isinstance(service._cloud_resource_repository, PostgresCloudResourceRepository)
    assert isinstance(service._compliance_repository, PostgresComplianceRepository)
