import pytest

from src.modules.iam_analysis.evaluation import ComparativeEvaluationEngine


def test_comparison_uses_observed_path_risk_and_execution_evidence() -> None:
    result = ComparativeEvaluationEngine().evaluate(
        baseline_path_risks=[90, 60],
        final_path_risks=[30],
        attempts=[
            {"execution_status": "applied", "verification_passed": True},
            {"execution_status": "applied", "verification_passed": False},
        ],
        applied_permission_changes={"user:alice:s3:GetObject:bucket/*", "role:worker:s3:PutObject:bucket/*"},
        necessary_permission_changes={"user:alice:s3:GetObject:bucket/*"},
        replanning_attempts=1,
        execution_time_seconds=2.5,
    )

    assert result.attack_path_reduction_percent == 50
    assert result.baseline_average_risk == 75
    assert result.final_average_risk == 30
    assert result.risk_reduction_percent == 60
    assert result.remediation_success_rate == 1
    assert result.verification_success_rate == 0.5
    assert result.unnecessary_permission_changes == 1
    assert result.replanning_attempts == 1
    assert result.execution_time_seconds == 2.5


def test_comparison_marks_reductions_not_applicable_without_baseline_paths() -> None:
    result = ComparativeEvaluationEngine().evaluate(
        baseline_path_risks=[],
        final_path_risks=[],
        attempts=[],
        applied_permission_changes=set(),
        necessary_permission_changes=set(),
        replanning_attempts=0,
        execution_time_seconds=0,
    )

    assert result.attack_path_reduction_percent is None
    assert result.risk_reduction_percent is None
    assert result.remediation_success_rate is None
    assert result.verification_success_rate is None


def test_comparison_reports_full_risk_reduction_when_all_paths_are_eliminated() -> None:
    result = ComparativeEvaluationEngine().evaluate(
        baseline_path_risks=[62, 82],
        final_path_risks=[],
        attempts=[{"execution_status": "applied", "verification_passed": True}],
        applied_permission_changes={"user:alice:sts:AssumeRole:role/worker"},
        necessary_permission_changes={"user:alice:sts:AssumeRole:role/worker"},
        replanning_attempts=0,
        execution_time_seconds=1.5,
    )

    assert result.final_average_risk == 0
    assert result.risk_reduction_percent == 100


def test_comparison_rejects_invalid_scores_and_negative_durations() -> None:
    engine = ComparativeEvaluationEngine()

    with pytest.raises(ValueError, match="between 0 and 100"):
        engine.evaluate(
            baseline_path_risks=[101],
            final_path_risks=[],
            attempts=[],
            applied_permission_changes=set(),
            necessary_permission_changes=set(),
            replanning_attempts=0,
            execution_time_seconds=0,
        )
    with pytest.raises(ValueError, match="cannot be negative"):
        engine.evaluate(
            baseline_path_risks=[],
            final_path_risks=[],
            attempts=[],
            applied_permission_changes=set(),
            necessary_permission_changes=set(),
            replanning_attempts=0,
            execution_time_seconds=-1,
        )
