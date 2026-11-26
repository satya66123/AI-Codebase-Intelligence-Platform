
"""Tests for the advanced intelligence integration service."""

from types import SimpleNamespace

import pytest

from appy.application.advanced_intelligence_integration_service import (
    AdvancedIntelligenceIntegrationError,
    AdvancedIntelligenceIntegrationResult,
    AdvancedIntelligenceIntegrationService,
)


class FakeInvestigationAgent:
    def __init__(self, result=None, error=None, events=None):
        self.result = result or SimpleNamespace(name="investigation")
        self.error = error
        self.events = events if events is not None else []
        self.received = None

    def investigate(self, **kwargs):
        self.events.append("investigation")
        self.received = kwargs
        if self.error:
            raise self.error
        return self.result


class FakeReportService:
    def __init__(self, result=None, error=None, events=None):
        self.result = result or SimpleNamespace(
            report_text="Architecture report",
            sections=(),
            recommendations=(),
        )
        self.error = error
        self.events = events if events is not None else []
        self.received = None

    def generate(self, investigation_result):
        self.events.append("report")
        self.received = investigation_result
        if self.error:
            raise self.error
        return self.result


class FakeEvaluationService:
    def __init__(self, result=None, error=None, events=None):
        self.result = result or SimpleNamespace(
            overall_score=95.0,
            overall_level="high",
            recommendations=("Review architecture evidence.",),
        )
        self.error = error
        self.events = events if events is not None else []
        self.received = None

    def evaluate(self, **kwargs):
        self.events.append("evaluation")
        self.received = kwargs
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def parsed_sources():
    return {
        "appy.py": SimpleNamespace(
            filename="appy.py",
            language="python",
        )
    }


@pytest.fixture
def integration_parts():
    events = []
    investigation = FakeInvestigationAgent(events=events)
    report = FakeReportService(events=events)
    evaluation = FakeEvaluationService(events=events)

    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=investigation,
        report_service=report,
        evaluation_service=evaluation,
    )

    return service, investigation, report, evaluation, events


def test_constructor_accepts_injected_services(integration_parts):
    service, investigation, report, evaluation, _ = integration_parts

    assert service.investigation_agent is investigation
    assert service.report_service is report
    assert service.evaluation_service is evaluation


def test_successful_integration_returns_unified_result(
    integration_parts,
    parsed_sources,
):
    service, investigation, report, evaluation, _ = integration_parts

    result = service.integrate(parsed_sources)

    assert isinstance(result, AdvancedIntelligenceIntegrationResult)
    assert result.investigation_result is investigation.result
    assert result.report is report.result
    assert result.evaluation is evaluation.result


def test_integration_runs_stages_in_correct_order(
    integration_parts,
    parsed_sources,
):
    service, _, _, _, events = integration_parts

    service.integrate(parsed_sources)

    assert events == [
        "investigation",
        "report",
        "evaluation",
    ]


def test_report_receives_investigation_result(
    integration_parts,
    parsed_sources,
):
    service, investigation, report, _, _ = integration_parts

    service.integrate(parsed_sources)

    assert report.received is investigation.result


def test_evaluation_receives_investigation_and_report(
    integration_parts,
    parsed_sources,
):
    service, investigation, report, evaluation, _ = integration_parts

    service.integrate(parsed_sources)

    assert evaluation.received["investigation_result"] is investigation.result
    assert evaluation.received["report"] is report.result


def test_investigation_receives_all_analysis_arguments(
    integration_parts,
    parsed_sources,
):
    service, investigation, _, _, _ = integration_parts

    service.integrate(
        parsed_sources=parsed_sources,
        source_files=("appy.py",),
        code_entities=("entity-1",),
        dependencies=("dependency-1",),
        call_graphs=("call-1",),
        entry_points=("appy.main",),
        max_depth=5,
    )

    assert investigation.received == {
        "parsed_sources": parsed_sources,
        "source_files": ("appy.py",),
        "code_entities": ("entity-1",),
        "dependencies": ("dependency-1",),
        "call_graphs": ("call-1",),
        "entry_points": ("appy.main",),
        "max_depth": 5,
    }


def test_optional_impact_results_are_forwarded(
    integration_parts,
    parsed_sources,
):
    service, _, _, evaluation, _ = integration_parts
    change_impact = object()
    direct_indirect_impact = object()

    service.integrate(
        parsed_sources,
        change_impact_result=change_impact,
        direct_indirect_impact_result=direct_indirect_impact,
    )

    assert evaluation.received["change_impact_result"] is change_impact
    assert (
        evaluation.received["direct_indirect_impact_result"]
        is direct_indirect_impact
    )


def test_optional_impact_results_default_to_none(
    integration_parts,
    parsed_sources,
):
    service, _, _, evaluation, _ = integration_parts

    service.integrate(parsed_sources)

    assert evaluation.received["change_impact_result"] is None
    assert evaluation.received["direct_indirect_impact_result"] is None


def test_default_analysis_arguments_are_forwarded(
    integration_parts,
    parsed_sources,
):
    service, investigation, _, _, _ = integration_parts

    service.integrate(parsed_sources)

    assert investigation.received["source_files"] is None
    assert investigation.received["code_entities"] == ()
    assert investigation.received["dependencies"] == ()
    assert investigation.received["call_graphs"] == ()
    assert investigation.received["entry_points"] is None
    assert investigation.received["max_depth"] == 10


@pytest.mark.parametrize(
    "parsed_sources",
    [
        None,
        (),
        [],
        "appy.py",
        123,
    ],
)
def test_invalid_parsed_sources_are_rejected(parsed_sources):
    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=FakeInvestigationAgent(),
        report_service=FakeReportService(),
        evaluation_service=FakeEvaluationService(),
    )

    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="parsed_sources must be a mapping",
    ) as error:
        service.integrate(parsed_sources)

    assert error.value.stage == "validation"


def test_empty_parsed_sources_are_rejected():
    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=FakeInvestigationAgent(),
        report_service=FakeReportService(),
        evaluation_service=FakeEvaluationService(),
    )

    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="parsed_sources must not be empty",
    ) as error:
        service.integrate({})

    assert error.value.stage == "validation"


def test_investigation_failure_identifies_stage(parsed_sources):
    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=FakeInvestigationAgent(
            error=RuntimeError("investigation failed")
        ),
        report_service=FakeReportService(),
        evaluation_service=FakeEvaluationService(),
    )

    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="Advanced investigation failed",
    ) as error:
        service.integrate(parsed_sources)

    assert error.value.stage == "investigation"


def test_report_failure_identifies_stage(parsed_sources):
    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=FakeInvestigationAgent(),
        report_service=FakeReportService(
            error=RuntimeError("report failed")
        ),
        evaluation_service=FakeEvaluationService(),
    )

    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="Architecture report generation failed",
    ) as error:
        service.integrate(parsed_sources)

    assert error.value.stage == "report"


def test_evaluation_failure_identifies_stage(parsed_sources):
    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=FakeInvestigationAgent(),
        report_service=FakeReportService(),
        evaluation_service=FakeEvaluationService(
            error=RuntimeError("evaluation failed")
        ),
    )

    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="Advanced analysis evaluation failed",
    ) as error:
        service.integrate(parsed_sources)

    assert error.value.stage == "evaluation"


def test_report_is_not_generated_when_investigation_fails(parsed_sources):
    events = []
    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=FakeInvestigationAgent(
            error=RuntimeError("failed"),
            events=events,
        ),
        report_service=FakeReportService(events=events),
        evaluation_service=FakeEvaluationService(events=events),
    )

    with pytest.raises(AdvancedIntelligenceIntegrationError):
        service.integrate(parsed_sources)

    assert events == ["investigation"]


def test_evaluation_is_not_run_when_report_fails(parsed_sources):
    events = []
    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=FakeInvestigationAgent(events=events),
        report_service=FakeReportService(
            error=RuntimeError("failed"),
            events=events,
        ),
        evaluation_service=FakeEvaluationService(events=events),
    )

    with pytest.raises(AdvancedIntelligenceIntegrationError):
        service.integrate(parsed_sources)

    assert events == ["investigation", "report"]


def test_result_contains_completed_stages(
    integration_parts,
    parsed_sources,
):
    service, _, _, _, _ = integration_parts

    result = service.integrate(parsed_sources)

    assert result.completed_stages == (
        "investigation",
        "report",
        "evaluation",
    )


def test_result_is_complete(
    integration_parts,
    parsed_sources,
):
    service, _, _, _, _ = integration_parts

    result = service.integrate(parsed_sources)

    assert result.is_complete is True


def test_result_exposes_overall_score(
    integration_parts,
    parsed_sources,
):
    service, _, _, _, _ = integration_parts

    result = service.integrate(parsed_sources)

    assert result.overall_score == 95.0


def test_result_exposes_overall_level(
    integration_parts,
    parsed_sources,
):
    service, _, _, _, _ = integration_parts

    result = service.integrate(parsed_sources)

    assert result.overall_level == "high"


def test_result_exposes_recommendations(
    integration_parts,
    parsed_sources,
):
    service, _, _, _, _ = integration_parts

    result = service.integrate(parsed_sources)

    assert result.recommendations == (
        "Review architecture evidence.",
    )


def test_result_exposes_report_text(
    integration_parts,
    parsed_sources,
):
    service, _, _, _, _ = integration_parts

    result = service.integrate(parsed_sources)

    assert result.report_text == "Architecture report"


@pytest.mark.parametrize(
    "field_name",
    [
        "investigation_result",
        "report",
        "evaluation",
    ],
)
def test_result_rejects_missing_stage_result(field_name):
    values = {
        "investigation_result": object(),
        "report": object(),
        "evaluation": object(),
        "completed_stages": (
            "investigation",
            "report",
            "evaluation",
        ),
    }
    values[field_name] = None

    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match=f"{field_name} cannot be None",
    ):
        AdvancedIntelligenceIntegrationResult(**values)


def test_result_rejects_non_tuple_completed_stages():
    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="completed_stages must be a tuple",
    ):
        AdvancedIntelligenceIntegrationResult(
            investigation_result=object(),
            report=object(),
            evaluation=object(),
            completed_stages=[
                "investigation",
                "report",
                "evaluation",
            ],
        )


def test_result_rejects_empty_stage_name():
    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="non-empty strings",
    ):
        AdvancedIntelligenceIntegrationResult(
            investigation_result=object(),
            report=object(),
            evaluation=object(),
            completed_stages=(
                "investigation",
                "",
                "evaluation",
            ),
        )


def test_result_rejects_incomplete_stage_sequence():
    with pytest.raises(
        AdvancedIntelligenceIntegrationError,
        match="execution order",
    ):
        AdvancedIntelligenceIntegrationResult(
            investigation_result=object(),
            report=object(),
            evaluation=object(),
            completed_stages=("investigation", "report"),
        )


def test_injected_falsey_service_is_not_replaced():
    class FalseyInvestigationAgent(FakeInvestigationAgent):
        def __bool__(self):
            return False

    investigation = FalseyInvestigationAgent()
    report = FakeReportService()
    evaluation = FakeEvaluationService()

    service = AdvancedIntelligenceIntegrationService(
        investigation_agent=investigation,
        report_service=report,
        evaluation_service=evaluation,
    )

    assert service.investigation_agent is investigation
