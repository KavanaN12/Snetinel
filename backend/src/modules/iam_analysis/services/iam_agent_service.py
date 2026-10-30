from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import boto3
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.attack_path.repositories.attack_path_repository import AttackPathRepository
from src.modules.attack_path.services.attack_path_service import AttackPathService
from src.modules.graph.repositories.graph_repository import GraphRepository
from src.modules.graph.services.graph_service import GraphService
from src.modules.iam_analysis.agent import (
    AgentAnalysis,
    AgentObservation,
    AgentRunResult,
    AutonomousIamAgent,
)
from src.modules.iam_analysis.domain.entities import IamAgentRun
from src.modules.iam_analysis.remediation import LocalStackIamExecutor
from src.modules.iam_analysis.repositories.agent_run_repository import AgentRunRepository
from src.modules.discovery.repositories.cloud_resource_repository import CloudResourceRepository
from src.modules.discovery.repositories.discovery_repository import DiscoveryRepository
from src.modules.discovery.services.cloud_discovery_service import CloudDiscoveryService
from src.modules.risk_scoring.repositories.finding_repository import FindingRepository
from src.modules.risk_scoring.risk_engine import DeterministicRiskEngine
from src.modules.risk_scoring.services.risk_scoring_service import RiskScoringService
from src.modules.scenarios.repositories import ScenarioRunRepository
from src.modules.workspace.domain.exceptions import WorkspaceAccessDeniedError, WorkspaceNotFoundError
from src.modules.workspace.repositories.workspace_repository import WorkspaceRepository
from src.shared.config.settings import get_settings


class IamAgentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        workspace_repository: WorkspaceRepository,
        discovery_repository: DiscoveryRepository,
        cloud_resource_repository: CloudResourceRepository,
        graph_repository: GraphRepository,
        attack_path_repository: AttackPathRepository,
        finding_repository: FindingRepository,
        agent_run_repository: AgentRunRepository,
        endpoint_url: str | None = None,
        scenario_run_repository: ScenarioRunRepository | None = None,
    ) -> None:
        self._session = session
        self._workspaces = workspace_repository
        self._discovery_runs = discovery_repository
        self._cloud_resources = cloud_resource_repository
        self._graphs = graph_repository
        self._attack_paths = attack_path_repository
        self._findings = finding_repository
        self._agent_runs = agent_run_repository
        self._scenario_runs = scenario_run_repository
        settings = get_settings()
        self._endpoint_url = endpoint_url or settings.AWS_ENDPOINT_URL
        self._settings = settings

    async def run(
        self,
        workspace_id: UUID | str,
        current_user_id: UUID | str,
        *,
        max_attempts: int = 5,
    ) -> IamAgentRun:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")
        if str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceAccessDeniedError("You do not own this workspace")
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5")

        aws_session = boto3.Session(
            aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY,
            region_name=self._settings.AWS_REGION,
        )
        iam_client = aws_session.client(
            "iam",
            endpoint_url=self._endpoint_url,
            region_name=self._settings.AWS_REGION,
        )
        executor = LocalStackIamExecutor(iam_client, self._endpoint_url)
        executor.check_ready()

        async def observe() -> AgentObservation:
            started_at = datetime.now(timezone.utc)
            discovery_run = await self._discovery_runs.create(
                workspace_id=workspace.id,
                status="running",
                summary="Autonomous agent is collecting a fresh LocalStack snapshot",
                resource_count=0,
                discovered_resources=[],
                started_at=started_at,
                completed_at=None,
            )
            cloud_discovery = CloudDiscoveryService(
                self._discovery_runs,
                self._workspaces,
                self._cloud_resources,
                scenario_run_repository=self._scenario_runs,
            )
            discovered_count = await cloud_discovery.process_discovery_job(
                workspace_id=workspace.id,
                discovery_run_id=discovery_run.id,
            )
            graph_service = GraphService(
                workspace_repository=self._workspaces,
                cloud_resource_repository=self._cloud_resources,
                graph_repository=self._graphs,
            )
            graph = await graph_service.build_graph(workspace.id, current_user_id)
            await self._session.commit()
            return AgentObservation(
                nodes=graph.nodes,
                edges=graph.edges,
                metadata={
                    "discovery_run_id": str(discovery_run.id),
                    "resource_count": discovered_count,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        async def analyze(observation: AgentObservation) -> AgentAnalysis:
            path_service = AttackPathService(
                workspace_repository=self._workspaces,
                graph_repository=self._graphs,
                attack_path_repository=self._attack_paths,
            )
            path_result = await path_service.analyze(workspace.id, current_user_id)
            observed_node_ids = {str(node.id) for node in observation.nodes}
            if any(
                str(step.get("id")) not in observed_node_ids
                for path in path_result.paths
                for step in path.steps
            ):
                raise RuntimeError("Attack-path analysis returned nodes outside the observed graph")
            risk_service = RiskScoringService(
                workspace_repository=self._workspaces,
                attack_path_repository=self._attack_paths,
                finding_repository=self._findings,
            )
            await risk_service.generate_findings(workspace.id, current_user_id)
            await self._session.commit()
            risk_engine = DeterministicRiskEngine()
            return AgentAnalysis(
                paths=path_result.paths,
                risk_scores={
                    str(path.id): risk_engine.assess(
                        path.attack_type,
                        path.steps,
                        path.details or {},
                    ).score
                    for path in path_result.paths
                },
            )

        agent = AutonomousIamAgent(
            observe=observe,
            analyze=analyze,
            executor=executor,
            max_attempts=max_attempts,
        )
        result: AgentRunResult = await agent.run()
        run = await self._agent_runs.create(
            workspace_id=workspace.id,
            status=result.status,
            lifecycle=result.lifecycle,
            attempts=result.attempts,
            baseline_path_count=result.baseline_path_count,
            final_path_count=result.final_path_count,
            evaluation=result.evaluation,
        )
        await self._session.commit()
        return run

    async def list_runs(
        self,
        workspace_id: UUID | str,
        current_user_id: UUID | str,
    ) -> list[IamAgentRun]:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found")
        if str(workspace.owner_id) != str(current_user_id):
            raise WorkspaceAccessDeniedError("You do not own this workspace")
        return await self._agent_runs.list_for_workspace(workspace.id)
