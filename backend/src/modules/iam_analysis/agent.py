from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from src.modules.iam_analysis.evaluation import ComparativeEvaluationEngine
from src.modules.iam_analysis.remediation import (
    LocalStackIamExecutor,
    RemediationPlanner,
)
from src.modules.risk_scoring.risk_engine import DeterministicRiskEngine


@dataclass(slots=True)
class AgentObservation:
    nodes: list[Any]
    edges: list[Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentAnalysis:
    paths: list[Any]
    risk_scores: dict[str, int]


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    status: str
    lifecycle: list[dict[str, Any]]
    attempts: list[dict[str, Any]]
    baseline_path_count: int
    final_path_count: int
    evaluation: dict[str, Any]


class AutonomousIamAgent:
    """Runs bounded, evidence-led remediation with fresh post-change analysis."""

    def __init__(
        self,
        *,
        observe: Callable[[], Awaitable[AgentObservation]],
        analyze: Callable[[AgentObservation], Awaitable[AgentAnalysis]],
        executor: LocalStackIamExecutor,
        planner: RemediationPlanner | None = None,
        max_attempts: int = 5,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("At least one remediation attempt must be allowed")
        self._observe = observe
        self._analyze = analyze
        self._executor = executor
        self._planner = planner or RemediationPlanner()
        self._max_attempts = max_attempts
        self._risk_engine = DeterministicRiskEngine()
        self._evaluation_engine = ComparativeEvaluationEngine()

    async def run(self) -> AgentRunResult:
        started = time.monotonic()
        lifecycle: list[dict[str, Any]] = []
        attempts: list[dict[str, Any]] = []
        applied_changes: set[str] = set()
        necessary_changes: set[str] = set()

        self._stage(lifecycle, "OBSERVE", "started")
        observation = await self._observe()
        self._stage(
            lifecycle,
            "OBSERVE",
            "completed",
            node_count=len(observation.nodes),
            edge_count=len(observation.edges),
            **observation.metadata,
        )
        self._stage(lifecycle, "ANALYSE", "started")
        analysis = await self._analyze(observation)
        self._stage(lifecycle, "ANALYSE", "completed", path_count=len(analysis.paths))
        baseline_paths = list(analysis.paths)
        baseline_risks = [
            analysis.risk_scores.get(str(path.id), 0)
            for path in baseline_paths
        ]
        self._stage(lifecycle, "PRIORITISE", "completed", path_count=len(baseline_paths))

        if not baseline_paths:
            self._stage(lifecycle, "REPORT", "completed")
            return self._result(
                status="no_findings",
                lifecycle=lifecycle,
                attempts=attempts,
                baseline_risks=baseline_risks,
                final_risks=[],
                applied_changes=applied_changes,
                necessary_changes=necessary_changes,
                replanning_attempts=0,
                execution_seconds=time.monotonic() - started,
                final_path_count=0,
            )

        target_key = self._path_key(
            max(
                baseline_paths,
                key=lambda path: analysis.risk_scores.get(str(path.id), 0),
            )
        )
        resolved_target_keys: set[tuple[tuple[str, str], tuple[str, str]]] = set()
        status = "attempt_limit_reached"
        replan_count = 0

        for attempt_number in range(1, self._max_attempts + 1):
            candidate_paths = [
                path for path in analysis.paths if self._path_key(path) == target_key
            ]
            if not candidate_paths:
                if not analysis.paths:
                    status = "verified"
                    break
                remaining_paths = [
                    path
                    for path in analysis.paths
                    if self._path_key(path) not in resolved_target_keys
                ]
                if not remaining_paths:
                    status = "blocked"
                    break
                target_key = self._path_key(
                    max(
                        remaining_paths,
                        key=lambda path: analysis.risk_scores.get(str(path.id), 0),
                    )
                )
                candidate_paths = [
                    path for path in remaining_paths if self._path_key(path) == target_key
                ]
            self._stage(
                lifecycle,
                "PRIORITISE",
                "completed",
                attempt=attempt_number,
                path_count=len(analysis.paths),
            )

            self._stage(
                lifecycle,
                "DECIDE",
                "started",
                attempt=attempt_number,
                candidate_count=len(candidate_paths),
            )
            path = max(
                candidate_paths,
                key=lambda candidate: analysis.risk_scores.get(str(candidate.id), 0),
            )
            plan = self._planner.select(path, observation.nodes, applied_changes)
            if plan is None:
                self._stage(lifecycle, "DECIDE", "blocked", reason="No safely remediable edge in evidence")
                status = "blocked"
                break
            self._stage(
                lifecycle,
                "DECIDE",
                "completed",
                strategy=plan.strategy,
                principal=plan.principal_name,
            )
            self._stage(
                lifecycle,
                "PLAN",
                "completed",
                action=plan.action,
                resource_arn=plan.resource_arn,
                reason=plan.reason,
                operational_impact=plan.operational_impact,
            )

            self._stage(lifecycle, "EXECUTE", "started", attempt=attempt_number)
            execution = self._executor.execute(plan)
            change_key = f"{plan.principal_type}:{plan.principal_name}:{plan.action}:{plan.resource_arn}"
            applied_changes.add(change_key)
            self._stage(
                lifecycle,
                "EXECUTE",
                "completed",
                policy_name=execution.policy_name,
                execution_status=execution.status,
            )

            self._stage(lifecycle, "VERIFY", "started", attempt=attempt_number)
            self._stage(lifecycle, "OBSERVE", "started", attempt=attempt_number)
            observation = await self._observe()
            self._stage(
                lifecycle,
                "OBSERVE",
                "completed",
                attempt=attempt_number,
                node_count=len(observation.nodes),
                edge_count=len(observation.edges),
                **observation.metadata,
            )
            self._stage(lifecycle, "ANALYSE", "started", attempt=attempt_number)
            analysis = await self._analyze(observation)
            self._stage(lifecycle, "ANALYSE", "completed", attempt=attempt_number)
            remaining_target_paths = [
                candidate for candidate in analysis.paths if self._path_key(candidate) == target_key
            ]
            verification_passed = not remaining_target_paths
            if len(remaining_target_paths) < len(candidate_paths):
                necessary_changes.add(change_key)
            attempts.append(
                {
                    "attempt": attempt_number,
                    "action": plan.action,
                    "resource_arn": plan.resource_arn,
                    "principal_type": plan.principal_type,
                    "principal_name": plan.principal_name,
                    "execution_status": execution.status,
                    "execution_verified": execution.verified,
                    "verification_passed": verification_passed,
                    "remaining_target_paths": len(remaining_target_paths),
                    "remaining_attack_paths": len(analysis.paths),
                    "rollback": execution.rollback,
                }
            )
            self._stage(
                lifecycle,
                "VERIFY",
                "completed" if verification_passed else "failed",
                attempt=attempt_number,
                remaining_target_paths=len(remaining_target_paths),
                remaining_attack_paths=len(analysis.paths),
            )
            if verification_passed:
                resolved_target_keys.add(target_key)
                if not analysis.paths:
                    status = "verified"
                    break
                remaining_paths = [
                    path
                    for path in analysis.paths
                    if self._path_key(path) not in resolved_target_keys
                ]
                if not remaining_paths:
                    status = "blocked"
                    break
                if attempt_number >= self._max_attempts:
                    status = "attempt_limit_reached"
                    break
                target_path = max(
                    remaining_paths,
                    key=lambda candidate: analysis.risk_scores.get(str(candidate.id), 0),
                )
                target_key = self._path_key(target_path)
                replan_count += 1
                self._stage(
                    lifecycle,
                    "RE-PLAN",
                    "started",
                    attempt=attempt_number + 1,
                    reason=(
                        f"The selected path was eliminated; {len(analysis.paths)} other "
                        "attack path(s) remain, so the highest-risk path was selected"
                    ),
                )
                self._stage(lifecycle, "RE-PLAN", "completed", attempt=attempt_number + 1)
                continue
            if attempt_number < self._max_attempts:
                replan_count += 1
                self._stage(
                    lifecycle,
                    "RE-PLAN",
                    "started",
                    attempt=attempt_number + 1,
                    reason="The original source-to-target attack path remains after recollection",
                )
                self._stage(lifecycle, "RE-PLAN", "completed", attempt=attempt_number + 1)

        final_risks = [
            analysis.risk_scores.get(str(path.id), 0)
            for path in analysis.paths
        ]
        execution_seconds = time.monotonic() - started
        evaluation = self._evaluation_engine.evaluate(
            baseline_path_risks=baseline_risks,
            final_path_risks=final_risks,
            attempts=attempts,
            applied_permission_changes=applied_changes,
            necessary_permission_changes=necessary_changes,
            replanning_attempts=replan_count,
            execution_time_seconds=execution_seconds,
        )
        self._stage(lifecycle, "REPORT", "completed", run_status=status)
        return AgentRunResult(
            status=status,
            lifecycle=lifecycle,
            attempts=attempts,
            baseline_path_count=len(baseline_paths),
            final_path_count=len(analysis.paths),
            evaluation=asdict(evaluation),
        )

    @staticmethod
    def _path_key(path: Any) -> tuple[tuple[str, str], tuple[str, str]]:
        steps = path.steps
        first = steps[0] if steps else {}
        last = steps[-1] if steps else {}
        return (
            (str(first.get("node_type", "")), str(first.get("external_id", ""))),
            (str(last.get("node_type", "")), str(last.get("external_id", ""))),
        )

    @staticmethod
    def _stage(
        lifecycle: list[dict[str, Any]],
        stage: str,
        status: str,
        **details: Any,
    ) -> None:
        lifecycle.append(
            {
                "stage": stage,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **details,
            }
        )

    @staticmethod
    def _result(
        *,
        status: str,
        lifecycle: list[dict[str, Any]],
        attempts: list[dict[str, Any]],
        baseline_risks: list[float],
        final_risks: list[float],
        applied_changes: set[str],
        necessary_changes: set[str],
        replanning_attempts: int,
        execution_seconds: float,
        final_path_count: int,
    ) -> AgentRunResult:
        evaluation = ComparativeEvaluationEngine().evaluate(
            baseline_path_risks=baseline_risks,
            final_path_risks=final_risks,
            attempts=attempts,
            applied_permission_changes=applied_changes,
            necessary_permission_changes=necessary_changes,
            replanning_attempts=replanning_attempts,
            execution_time_seconds=execution_seconds,
        )
        return AgentRunResult(
            status=status,
            lifecycle=lifecycle,
            attempts=attempts,
            baseline_path_count=len(baseline_risks),
            final_path_count=final_path_count,
            evaluation=asdict(evaluation),
        )
