from types import SimpleNamespace

import pytest

from appy.application.advanced_analysis_evaluation_service import (
    AdvancedAnalysisEvaluationError,
    AdvancedAnalysisEvaluationResult,
    AdvancedAnalysisEvaluationService,
    AnalysisDimensionScore,
    EvaluationLevel,
)


def make_investigation(
    architecture=None,
    responsibilities=None,
    code_flow=None,
    execution_flow=None,
    cross_module=None,
    data_flow=None,
):
    return SimpleNamespace(
        total_files=2,
        analyzed_files=2,
        skipped_files=0,
        architecture_patterns=architecture or SimpleNamespace(
            patterns_detected=2,
            findings=(),
        ),
        module_responsibilities=responsibilities or SimpleNamespace(
            classified_modules=4,
            total_modules=4,
        ),
        code_flow=code_flow or SimpleNamespace(
            total_calls=10,
            resolved_calls=9,
            unresolved_calls=1,
        ),
        execution_flow=execution_flow or SimpleNamespace(
            total_calls=8,
            resolved_calls=8,
            unresolved_calls=0,
        ),
        cross_module_relationships=cross_module or SimpleNamespace(
            resolved_calls=5,
            unresolved_calls=0,
        ),
        data_flow=data_flow if data_flow is not None else (
            SimpleNamespace(file_path="appy/main.py", analyzed=True),
            SimpleNamespace(file_path="appy/service.py", analyzed=True),
        ),
    )


def make_report(section_count=8, recommendations=("Review module boundaries.",)):
    return SimpleNamespace(
        sections=tuple(
            SimpleNamespace(title=f"Section {index}")
            for index in range(section_count)
        ),
        recommendations=recommendations,
        report_text="Architecture intelligence report",
    )


def make_change_impact_result(findings=None):
    if findings is None:
        findings = (
            SimpleNamespace(
                source_file="appy/service.py",
                affected_file="appy/service.py",
                relationship_type="function_call",
                changed_target="appy/core.py",
                affected_entity="service.run",
                reason="Calls changed function.",
            ),
        )

    return SimpleNamespace(findings=findings)


def make_direct_indirect_result(findings=None):
    if findings is None:
        findings = (
            SimpleNamespace(
                path=("appy.main", "appy.service", "appy.repository"),
                relationship_types=("function_call", "import"),
            ),
        )

    return SimpleNamespace(findings=findings)


def test_evaluate_returns_structured_result():
    service = AdvancedAnalysisEvaluationService()

    result = service.evaluate(make_investigation())

    assert isinstance(result, AdvancedAnalysisEvaluationResult)
    assert result.overall_score > 0
    assert result.overall_level in EvaluationLevel
    assert len(result.dimensions) == 5


def test_evaluate_includes_all_core_dimensions():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation()
    )

    names = {item.name for item in result.dimensions}

    assert names == {
        "architecture",
        "code_flow",
        "execution_flow",
        "cross_module_relationships",
        "data_flow",
    }


def test_evaluate_includes_optional_dimensions_when_supplied():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation(),
        report=make_report(),
        change_impact_result=make_change_impact_result(),
        direct_indirect_impact_result=make_direct_indirect_result(),
    )

    names = {item.name for item in result.dimensions}

    assert "report" in names
    assert "change_impact" in names
    assert "direct_indirect_impact" in names
    assert len(result.dimensions) == 8


def test_architecture_score_uses_module_classification_coverage():
    investigation = make_investigation(
        responsibilities=SimpleNamespace(
            classified_modules=3,
            total_modules=4,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "architecture"
    )

    assert dimension.score == 75.0
    assert dimension.evaluated_items == 4
    assert dimension.successful_items == 3


def test_architecture_zero_modules_is_treated_as_evaluated():
    investigation = make_investigation(
        responsibilities=SimpleNamespace(
            classified_modules=0,
            total_modules=0,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "architecture"
    )

    assert dimension.score == 100.0


def test_code_flow_score_uses_resolved_calls():
    investigation = make_investigation(
        code_flow=SimpleNamespace(
            total_calls=10,
            resolved_calls=7,
            unresolved_calls=3,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "code_flow"
    )

    assert dimension.score == 70.0
    assert dimension.successful_items == 7
    assert dimension.evaluated_items == 10


def test_code_flow_zero_calls_receives_full_resolution_score():
    investigation = make_investigation(
        code_flow=SimpleNamespace(
            total_calls=0,
            resolved_calls=0,
            unresolved_calls=0,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "code_flow"
    )

    assert dimension.score == 100.0


def test_execution_flow_score_uses_resolved_and_unresolved_calls():
    investigation = make_investigation(
        execution_flow=SimpleNamespace(
            resolved_calls=6,
            unresolved_calls=2,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "execution_flow"
    )

    assert dimension.score == 75.0


def test_cross_module_score_uses_resolution_coverage():
    investigation = make_investigation(
        cross_module=SimpleNamespace(
            resolved_calls=4,
            unresolved_calls=1,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "cross_module_relationships"
    )

    assert dimension.score == 80.0


def test_data_flow_score_counts_analyzed_files():
    investigation = make_investigation(
        data_flow=(
            SimpleNamespace(file_path="a.py", analyzed=True),
            SimpleNamespace(file_path="b.py", analyzed=False),
            SimpleNamespace(file_path="c.py", analyzed=True),
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "data_flow"
    )

    assert dimension.score == pytest.approx(66.67)
    assert dimension.evaluated_items == 3
    assert dimension.successful_items == 2


def test_data_flow_accepts_empty_result_tuple():
    investigation = make_investigation(data_flow=())

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    dimension = next(
        item for item in result.dimensions
        if item.name == "data_flow"
    )

    assert dimension.score == 100.0


def test_report_score_uses_expected_section_coverage():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation(),
        report=make_report(section_count=4),
    )

    dimension = next(
        item for item in result.dimensions
        if item.name == "report"
    )

    assert dimension.score == 50.0
    assert dimension.evaluated_items == 8
    assert dimension.successful_items == 4


def test_change_impact_checks_finding_traceability():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation(),
        change_impact_result=make_change_impact_result(),
    )

    dimension = next(
        item for item in result.dimensions
        if item.name == "change_impact"
    )

    assert dimension.score == 100.0


def test_change_impact_detects_incomplete_finding():
    incomplete = SimpleNamespace(
        source_file="appy/service.py",
        affected_file="appy/service.py",
        relationship_type="import",
        changed_target="appy/core.py",
        affected_entity="",
        reason="Missing entity.",
    )

    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation(),
        change_impact_result=make_change_impact_result((incomplete,)),
    )

    dimension = next(
        item for item in result.dimensions
        if item.name == "change_impact"
    )

    assert dimension.score == 0.0
    assert dimension.findings


def test_direct_indirect_impact_checks_relationship_paths():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation(),
        direct_indirect_impact_result=make_direct_indirect_result(),
    )

    dimension = next(
        item for item in result.dimensions
        if item.name == "direct_indirect_impact"
    )

    assert dimension.score == 100.0


def test_direct_indirect_impact_detects_incomplete_path():
    invalid = SimpleNamespace(
        path=("appy.main",),
        relationship_types=("function_call",),
    )

    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation(),
        direct_indirect_impact_result=make_direct_indirect_result((invalid,)),
    )

    dimension = next(
        item for item in result.dimensions
        if item.name == "direct_indirect_impact"
    )

    assert dimension.score == 0.0


def test_evaluation_generates_findings_for_low_scores():
    investigation = make_investigation(
        code_flow=SimpleNamespace(
            total_calls=10,
            resolved_calls=2,
            unresolved_calls=8,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    assert any(
        finding.dimension == "code_flow"
        for finding in result.findings
    )


def test_evaluation_generates_recommendations_for_low_scores():
    investigation = make_investigation(
        code_flow=SimpleNamespace(
            total_calls=10,
            resolved_calls=2,
            unresolved_calls=8,
        )
    )

    result = AdvancedAnalysisEvaluationService().evaluate(investigation)

    assert any(
        "unresolved calls" in item
        for item in result.recommendations
    )


def test_evaluation_calculates_overall_score_as_dimension_average():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation()
    )

    expected = round(
        sum(item.score for item in result.dimensions)
        / len(result.dimensions),
        2,
    )

    assert result.overall_score == expected


def test_evaluation_reports_analysis_coverage():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation()
    )

    assert result.evaluated_analyses == 6
    assert result.completed_analyses == 6
    assert result.coverage_percentage == 100.0


def test_evaluation_result_dimension_scores_property():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation()
    )

    scores = result.dimension_scores

    assert "architecture" in scores
    assert "data_flow" in scores


def test_evaluation_result_sufficiency_property():
    result = AdvancedAnalysisEvaluationService().evaluate(
        make_investigation()
    )

    assert result.is_sufficient is True


def test_evaluation_rejects_none_investigation():
    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="cannot be None",
    ):
        AdvancedAnalysisEvaluationService().evaluate(None)


def test_evaluation_rejects_missing_investigation_fields():
    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="missing required",
    ):
        AdvancedAnalysisEvaluationService().evaluate(
            SimpleNamespace(total_files=1)
        )


def test_evaluation_rejects_invalid_file_counts():
    investigation = make_investigation()
    investigation.total_files = -1

    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="non-negative integer",
    ):
        AdvancedAnalysisEvaluationService().evaluate(investigation)


def test_evaluation_rejects_inconsistent_file_counts():
    investigation = make_investigation()
    investigation.analyzed_files = 2
    investigation.skipped_files = 2
    investigation.total_files = 3

    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="inconsistent",
    ):
        AdvancedAnalysisEvaluationService().evaluate(investigation)


def test_evaluation_rejects_invalid_resolution_counts():
    investigation = make_investigation(
        code_flow=SimpleNamespace(
            total_calls=2,
            resolved_calls=2,
            unresolved_calls=2,
        )
    )

    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="exceed total calls",
    ):
        AdvancedAnalysisEvaluationService().evaluate(investigation)


def test_evaluation_rejects_invalid_data_flow_collection():
    investigation = make_investigation(data_flow="invalid")

    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="tuple or list",
    ):
        AdvancedAnalysisEvaluationService().evaluate(investigation)


def test_evaluation_rejects_invalid_data_flow_item():
    investigation = make_investigation(
        data_flow=(SimpleNamespace(file_path="a.py"),)
    )

    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="file_path and analyzed",
    ):
        AdvancedAnalysisEvaluationService().evaluate(investigation)


def test_evaluation_rejects_invalid_report_text():
    report = make_report()
    report.report_text = " "

    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="non-empty string",
    ):
        AdvancedAnalysisEvaluationService().evaluate(
            make_investigation(),
            report=report,
        )


def test_dimension_score_rejects_score_above_100():
    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="between 0 and 100",
    ):
        AnalysisDimensionScore(
            name="architecture",
            score=101,
            level=EvaluationLevel.HIGH,
            evaluated_items=1,
            successful_items=1,
        )


def test_dimension_score_rejects_successful_count_above_total():
    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="cannot exceed",
    ):
        AnalysisDimensionScore(
            name="architecture",
            score=100,
            level=EvaluationLevel.HIGH,
            evaluated_items=1,
            successful_items=2,
        )


def test_dimension_score_rejects_invalid_level():
    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="EvaluationLevel",
    ):
        AnalysisDimensionScore(
            name="architecture",
            score=100,
            level="excellent",
            evaluated_items=1,
            successful_items=1,
        )


def test_evaluation_result_rejects_completed_count_above_evaluated():
    with pytest.raises(
        AdvancedAnalysisEvaluationError,
        match="cannot exceed",
    ):
        AdvancedAnalysisEvaluationResult(
            overall_score=90,
            overall_level=EvaluationLevel.HIGH,
            dimensions=(),
            findings=(),
            recommendations=(),
            evaluated_analyses=2,
            completed_analyses=3,
        )


def test_evaluation_level_thresholds():
    assert AdvancedAnalysisEvaluationService._level(90) is EvaluationLevel.HIGH
    assert AdvancedAnalysisEvaluationService._level(75) is EvaluationLevel.MEDIUM
    assert AdvancedAnalysisEvaluationService._level(40) is EvaluationLevel.LOW
    assert (
        AdvancedAnalysisEvaluationService._level(0)
        is EvaluationLevel.INSUFFICIENT
    )