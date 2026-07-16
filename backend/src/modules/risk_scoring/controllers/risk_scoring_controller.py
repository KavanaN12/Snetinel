from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.repositories.postgres_attack_path_repository import PostgresAttackPathRepository
from src.modules.risk_scoring.repositories.postgres_finding_repository import PostgresFindingRepository
from src.modules.risk_scoring.schemas.responses import FindingEvaluationResponse, FindingResponse
from src.modules.risk_scoring.services.risk_scoring_service import RiskScoringService
from src.modules.workspace.domain.exceptions import WorkspaceNotFoundError
from src.modules.workspace.repositories.postgres_workspace_repository import PostgresWorkspaceRepository
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/risk-scoring", tags=["risk-scoring"])


def get_risk_scoring_service(session: AsyncSession = Depends(get_db_session)) -> RiskScoringService:
    workspace_repository = PostgresWorkspaceRepository(session)
    attack_path_repository = PostgresAttackPathRepository(session)
    finding_repository = PostgresFindingRepository(session)
    return RiskScoringService(
        workspace_repository=workspace_repository,
        attack_path_repository=attack_path_repository,
        finding_repository=finding_repository,
    )


@router.post("/workspaces/{workspace_id}/evaluate", response_model=FindingEvaluationResponse)
async def evaluate_findings(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: RiskScoringService = Depends(get_risk_scoring_service),
) -> FindingEvaluationResponse:
    try:
        result = await service.generate_findings(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FindingEvaluationResponse(
        workspace_id=result.workspace_id,
        finding_count=result.finding_count,
        findings=[
            FindingResponse(
                id=finding.id,
                workspace_id=finding.workspace_id,
                title=finding.title,
                description=finding.description,
                severity=finding.severity,
                status=finding.status,
                evidence_subgraph=finding.evidence_subgraph,
                affected_resource_ids=finding.affected_resource_ids,
            )
            for finding in result.findings
        ],
    )


@router.get("/workspaces/{workspace_id}/findings", response_model=FindingEvaluationResponse)
async def list_findings(
    workspace_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    service: RiskScoringService = Depends(get_risk_scoring_service),
) -> FindingEvaluationResponse:
    try:
        result = await service.list_findings(workspace_id, current_user_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FindingEvaluationResponse(
        workspace_id=result.workspace_id,
        finding_count=result.finding_count,
        findings=[
            FindingResponse(
                id=finding.id,
                workspace_id=finding.workspace_id,
                title=finding.title,
                description=finding.description,
                severity=finding.severity,
                status=finding.status,
                evidence_subgraph=finding.evidence_subgraph,
                affected_resource_ids=finding.affected_resource_ids,
            )
            for finding in result.findings
        ],
    )
