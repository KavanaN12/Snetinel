from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ComparativeEvaluation:
    baseline_attack_paths: int
    final_attack_paths: int
    attack_path_reduction_percent: float | None
    baseline_average_risk: float | None
    final_average_risk: float | None
    risk_reduction_percent: float | None
    remediation_success_rate: float | None
    verification_success_rate: float | None
    unnecessary_permission_changes: int
    replanning_attempts: int
    execution_time_seconds: float


class ComparativeEvaluationEngine:
    """Derives outcome metrics from observed before/after state and execution logs."""

    def evaluate(
        self,
        *,
        baseline_path_risks: list[float],
        final_path_risks: list[float],
        attempts: list[dict[str, Any]],
        applied_permission_changes: set[str],
        necessary_permission_changes: set[str],
        replanning_attempts: int,
        execution_time_seconds: float,
    ) -> ComparativeEvaluation:
        if replanning_attempts < 0:
            raise ValueError("Re-planning attempts cannot be negative")
        if execution_time_seconds < 0:
            raise ValueError("Execution time cannot be negative")
        if any(risk < 0 or risk > 100 for risk in baseline_path_risks + final_path_risks):
            raise ValueError("Risk scores must be between 0 and 100")

        baseline_average = self._average(baseline_path_risks)
        final_average = self._average(final_path_risks)
        if baseline_average is not None and not final_path_risks:
            final_average = 0.0
        baseline_count = len(baseline_path_risks)
        final_count = len(final_path_risks)
        path_reduction = (
            (baseline_count - final_count) / baseline_count * 100
            if baseline_count
            else None
        )
        risk_reduction = (
            (baseline_average - final_average) / baseline_average * 100
            if baseline_average is not None
            and baseline_average > 0
            and final_average is not None
            else None
        )

        verification_results = [
            attempt["verification_passed"]
            for attempt in attempts
            if isinstance(attempt.get("verification_passed"), bool)
        ]
        completed_executions = [
            attempt
            for attempt in attempts
            if attempt.get("execution_status") == "applied"
        ]
        remediation_success = (
            len(completed_executions) / len(attempts)
            if attempts
            else None
        )
        verification_success = (
            sum(verification_results) / len(verification_results)
            if verification_results
            else None
        )

        return ComparativeEvaluation(
            baseline_attack_paths=baseline_count,
            final_attack_paths=final_count,
            attack_path_reduction_percent=path_reduction,
            baseline_average_risk=baseline_average,
            final_average_risk=final_average,
            risk_reduction_percent=risk_reduction,
            remediation_success_rate=remediation_success,
            verification_success_rate=verification_success,
            unnecessary_permission_changes=len(
                applied_permission_changes - necessary_permission_changes
            ),
            replanning_attempts=replanning_attempts,
            execution_time_seconds=execution_time_seconds,
        )

    @staticmethod
    def _average(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None
