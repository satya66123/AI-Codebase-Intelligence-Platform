
"""Tests for the final application integration service."""

from types import SimpleNamespace

import pytest

from appy.application.final_application_integration_service import (
    FinalApplicationIntegrationError,
    FinalApplicationIntegrationResult,
    FinalApplicationIntegrationService,
)


class FakeWorkflowService:
    """Test double for the end-to-end workflow service."""

    def __init__(self, result=None, error=None):
        self.result = result or SimpleNamespace(
            is_complete=True,
            repository_file_count=2,
            completed_stages=(
                "input_validation",
                "advanced_intelligence_integration",
                "workflow_completed",
            ),
            report=SimpleNamespace(report_text="Architecture report"),
            evaluation=SimpleNamespace(overall_score=95.0),
            investigation_result=SimpleNamespace(name="investigation"),
        )
        self.error = error
        self.calls = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        return self.result


@pytest.fixture
def parsed_sources():
    return {
        "appy.py": SimpleNamespace(filename="appy.py", language="python"),
        "service.py": SimpleNamespace(filename="service.py", language="python"),
    }


@pytest.fixture
def workflow_service():
    return FakeWorkflowService()


@pytest.fixture
def application_service(workflow_service):
    return FinalApplicationIntegrationService(
        workflow_service=workflow_service
    )


def test_constructor_accepts_injected_workflow_service(workflow_service):
    service = FinalApplicationIntegrationService(
        workflow_service=workflow_service
    )

    assert service.workflow_service is workflow_service


def test_constructor_creates_default_workflow_service():
    service = FinalApplicationIntegrationService()

    assert service.workflow_service is not None


def test_execute_returns_application_result(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert isinstance(result, FinalApplicationIntegrationResult)
    assert result.is_successful is True


def test_execute_forwards_parsed_sources(
    application_service,
    workflow_service,
    parsed_sources,
):
    application_service.execute(parsed_sources)

    assert workflow_service.calls[0]["parsed_sources"] is parsed_sources


def test_execute_forwards_source_files(
    application_service,
    workflow_service,
    parsed_sources,
):
    source_files = {"appy.py": "print('hello')"}

    application_service.execute(
        parsed_sources,
        source_files=source_files,
    )

    assert workflow_service.calls[0]["source_files"] is source_files


def test_execute_forwards_code_entities(
    application_service,
    workflow_service,
    parsed_sources,
):
    code_entities = (SimpleNamespace(name="main"),)

    application_service.execute(
        parsed_sources,
        code_entities=code_entities,
    )

    assert workflow_service.calls[0]["code_entities"] is code_entities


def test_execute_forwards_dependencies(
    application_service,
    workflow_service,
    parsed_sources,
):
    dependencies = (SimpleNamespace(source="appy.py"),)

    application_service.execute(
        parsed_sources,
        dependencies=dependencies,
    )

    assert workflow_service.calls[0]["dependencies"] is dependencies


def test_execute_forwards_call_graphs(
    application_service,
    workflow_service,
    parsed_sources,
):
    call_graphs = (SimpleNamespace(name="main"),)

    application_service.execute(
        parsed_sources,
        call_graphs=call_graphs,
    )

    assert workflow_service.calls[0]["call_graphs"] is call_graphs


def test_execute_forwards_entry_points(
    application_service,
    workflow_service,
    parsed_sources,
):
    entry_points = ("appy.main",)

    application_service.execute(
        parsed_sources,
        entry_points=entry_points,
    )

    assert workflow_service.calls[0]["entry_points"] is entry_points


def test_execute_forwards_max_depth(
    application_service,
    workflow_service,
    parsed_sources,
):
    application_service.execute(parsed_sources, max_depth=15)

    assert workflow_service.calls[0]["max_depth"] == 15


def test_execute_forwards_change_impact_result(
    application_service,
    workflow_service,
    parsed_sources,
):
    impact_result = SimpleNamespace(name="change-impact")

    application_service.execute(
        parsed_sources,
        change_impact_result=impact_result,
    )

    assert workflow_service.calls[0]["change_impact_result"] is impact_result


def test_execute_forwards_direct_indirect_impact_result(
    application_service,
    workflow_service,
    parsed_sources,
):
    impact_result = SimpleNamespace(name="direct-indirect-impact")

    application_service.execute(
        parsed_sources,
        direct_indirect_impact_result=impact_result,
    )

    assert (
        workflow_service.calls[0]["direct_indirect_impact_result"]
        is impact_result
    )


def test_execute_forwards_default_optional_arguments(
    application_service,
    workflow_service,
    parsed_sources,
):
    application_service.execute(parsed_sources)

    call = workflow_service.calls[0]

    assert call["source_files"] is None
    assert call["code_entities"] == ()
    assert call["dependencies"] == ()
    assert call["call_graphs"] == ()
    assert call["entry_points"] is None
    assert call["max_depth"] == 10
    assert call["change_impact_result"] is None
    assert call["direct_indirect_impact_result"] is None


@pytest.mark.parametrize(
    "invalid_sources",
    [None, (), [], "appy.py", 123],
)
def test_execute_rejects_non_mapping_sources(invalid_sources):
    service = FinalApplicationIntegrationService(
        workflow_service=FakeWorkflowService()
    )

    with pytest.raises(FinalApplicationIntegrationError) as exc_info:
        service.execute(invalid_sources)

    assert exc_info.value.stage == "input_validation"


def test_execute_rejects_empty_sources():
    service = FinalApplicationIntegrationService(
        workflow_service=FakeWorkflowService()
    )

    with pytest.raises(FinalApplicationIntegrationError) as exc_info:
        service.execute({})

    assert exc_info.value.stage == "input_validation"


def test_execute_wraps_workflow_failure(parsed_sources):
    original_error = RuntimeError("workflow failed")
    service = FinalApplicationIntegrationService(
        workflow_service=FakeWorkflowService(error=original_error)
    )

    with pytest.raises(FinalApplicationIntegrationError) as exc_info:
        service.execute(parsed_sources)

    assert exc_info.value.stage == "workflow_execution"
    assert "workflow failed" in str(exc_info.value)
    assert exc_info.value.__cause__ is original_error


def test_execute_preserves_workflow_error_stage(parsed_sources):
    original_error = ValueError("integration failed")
    original_error.stage = "advanced_intelligence_integration"

    service = FinalApplicationIntegrationService(
        workflow_service=FakeWorkflowService(error=original_error)
    )

    with pytest.raises(FinalApplicationIntegrationError) as exc_info:
        service.execute(parsed_sources)

    assert exc_info.value.stage == "advanced_intelligence_integration"


def test_execute_rejects_none_workflow_result(parsed_sources):
    service = FinalApplicationIntegrationService(
        workflow_service=FakeWorkflowService()
    )
    service.workflow_service.result = None

    with pytest.raises(FinalApplicationIntegrationError) as exc_info:
        service.execute(parsed_sources)

    assert exc_info.value.stage == "workflow_execution"


def test_execute_rejects_incomplete_workflow_result(parsed_sources):
    incomplete_result = SimpleNamespace(
        is_complete=False,
        repository_file_count=2,
        completed_stages=("input_validation",),
    )
    service = FinalApplicationIntegrationService(
        workflow_service=FakeWorkflowService(result=incomplete_result)
    )

    with pytest.raises(FinalApplicationIntegrationError) as exc_info:
        service.execute(parsed_sources)

    assert exc_info.value.stage == "workflow_validation"


def test_result_contains_workflow_result(
    application_service,
    workflow_service,
    parsed_sources,
):
    result = application_service.execute(parsed_sources)

    assert result.workflow_result is workflow_service.result


def test_result_status_is_completed(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert result.status == "completed"


def test_result_reports_success(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert result.is_successful is True


def test_result_exposes_report(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert result.report.report_text == "Architecture report"


def test_result_exposes_evaluation(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert result.evaluation.overall_score == 95.0


def test_result_exposes_investigation(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert result.investigation_result.name == "investigation"


def test_result_exposes_repository_file_count(
    application_service,
    parsed_sources,
):
    result = application_service.execute(parsed_sources)

    assert result.repository_file_count == 2


def test_result_exposes_completed_stages(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert result.completed_stages == (
        "input_validation",
        "advanced_intelligence_integration",
        "workflow_completed",
    )


def test_result_contains_application_message(application_service, parsed_sources):
    result = application_service.execute(parsed_sources)

    assert "completed successfully" in result.message
    assert "2 repository files" in result.message


def test_result_rejects_none_workflow_result():
    with pytest.raises(ValueError):
        FinalApplicationIntegrationResult(
            workflow_result=None,
            status="completed",
            message="Completed",
        )


def test_result_rejects_invalid_status():
    with pytest.raises(ValueError):
        FinalApplicationIntegrationResult(
            workflow_result=SimpleNamespace(is_complete=True),
            status="failed",
            message="Completed",
        )


def test_result_rejects_empty_message():
    with pytest.raises(ValueError):
        FinalApplicationIntegrationResult(
            workflow_result=SimpleNamespace(is_complete=True),
            status="completed",
            message=" ",
        )


def test_result_rejects_incomplete_workflow():
    with pytest.raises(ValueError):
        FinalApplicationIntegrationResult(
            workflow_result=SimpleNamespace(is_complete=False),
            status="completed",
            message="Completed",
        )


def test_falsey_injected_service_is_not_replaced():
    class FalseyWorkflowService(FakeWorkflowService):
        def __bool__(self):
            return False

    workflow = FalseyWorkflowService()
    service = FinalApplicationIntegrationService(
        workflow_service=workflow
    )

    assert service.workflow_service is workflow
