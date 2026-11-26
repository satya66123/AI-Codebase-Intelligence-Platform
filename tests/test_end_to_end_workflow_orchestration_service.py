
"""Tests for the end-to-end workflow orchestration service."""

from types import SimpleNamespace

import pytest

from app.application.end_to_end_workflow_orchestration_service import (
    EndToEndWorkflowOrchestrationError,
    EndToEndWorkflowOrchestrationService,
    EndToEndWorkflowResult,
)


class FakeIntegrationService:
    """Test double for the advanced intelligence integration service."""

    def __init__(self, result=None, error=None):
        self.result = result or SimpleNamespace(
            investigation_result=SimpleNamespace(name="investigation"),
            report=SimpleNamespace(report_text="Architecture report"),
            evaluation=SimpleNamespace(overall_score=95.0),
        )
        self.error = error
        self.calls = []

    def integrate(self, **kwargs):
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        return self.result


@pytest.fixture
def parsed_sources():
    return {
        "app.py": SimpleNamespace(filename="app.py", language="python"),
        "service.py": SimpleNamespace(filename="service.py", language="python"),
    }


@pytest.fixture
def integration_service():
    return FakeIntegrationService()


@pytest.fixture
def orchestration_service(integration_service):
    return EndToEndWorkflowOrchestrationService(
        integration_service=integration_service
    )


def test_constructor_accepts_injected_integration_service(integration_service):
    service = EndToEndWorkflowOrchestrationService(
        integration_service=integration_service
    )

    assert service.integration_service is integration_service


def test_constructor_creates_default_integration_service():
    service = EndToEndWorkflowOrchestrationService()

    assert service.integration_service is not None


def test_execute_returns_workflow_result(orchestration_service, parsed_sources):
    result = orchestration_service.execute(parsed_sources)

    assert isinstance(result, EndToEndWorkflowResult)
    assert result.is_complete is True


def test_execute_counts_repository_files(orchestration_service, parsed_sources):
    result = orchestration_service.execute(parsed_sources)

    assert result.repository_file_count == 2


def test_execute_forwards_parsed_sources(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    orchestration_service.execute(parsed_sources)

    assert integration_service.calls[0]["parsed_sources"] is parsed_sources


def test_execute_forwards_source_files(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    source_files = {"app.py": "print('hello')"}

    orchestration_service.execute(
        parsed_sources,
        source_files=source_files,
    )

    assert integration_service.calls[0]["source_files"] is source_files


def test_execute_forwards_code_entities(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    code_entities = (SimpleNamespace(name="main"),)

    orchestration_service.execute(
        parsed_sources,
        code_entities=code_entities,
    )

    assert integration_service.calls[0]["code_entities"] is code_entities


def test_execute_forwards_dependencies(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    dependencies = (SimpleNamespace(source="app.py"),)

    orchestration_service.execute(
        parsed_sources,
        dependencies=dependencies,
    )

    assert integration_service.calls[0]["dependencies"] is dependencies


def test_execute_forwards_call_graphs(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    call_graphs = (SimpleNamespace(name="main"),)

    orchestration_service.execute(
        parsed_sources,
        call_graphs=call_graphs,
    )

    assert integration_service.calls[0]["call_graphs"] is call_graphs


def test_execute_forwards_entry_points(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    entry_points = ("app.main",)

    orchestration_service.execute(
        parsed_sources,
        entry_points=entry_points,
    )

    assert integration_service.calls[0]["entry_points"] is entry_points


def test_execute_forwards_max_depth(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    orchestration_service.execute(parsed_sources, max_depth=15)

    assert integration_service.calls[0]["max_depth"] == 15


def test_execute_forwards_change_impact_result(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    impact_result = SimpleNamespace(name="change-impact")

    orchestration_service.execute(
        parsed_sources,
        change_impact_result=impact_result,
    )

    assert integration_service.calls[0]["change_impact_result"] is impact_result


def test_execute_forwards_direct_indirect_impact_result(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    impact_result = SimpleNamespace(name="direct-indirect-impact")

    orchestration_service.execute(
        parsed_sources,
        direct_indirect_impact_result=impact_result,
    )

    assert (
        integration_service.calls[0]["direct_indirect_impact_result"]
        is impact_result
    )


def test_execute_forwards_default_optional_arguments(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    orchestration_service.execute(parsed_sources)

    call = integration_service.calls[0]

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
    [None, (), [], "app.py", 123],
)
def test_execute_rejects_non_mapping_parsed_sources(invalid_sources):
    service = EndToEndWorkflowOrchestrationService(
        integration_service=FakeIntegrationService()
    )

    with pytest.raises(EndToEndWorkflowOrchestrationError) as exc_info:
        service.execute(invalid_sources)

    assert exc_info.value.stage == "input_validation"


def test_execute_rejects_empty_parsed_sources():
    service = EndToEndWorkflowOrchestrationService(
        integration_service=FakeIntegrationService()
    )

    with pytest.raises(EndToEndWorkflowOrchestrationError) as exc_info:
        service.execute({})

    assert exc_info.value.stage == "input_validation"
    assert "empty" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_filename",
    ["", " ", None, 123],
)
def test_execute_rejects_invalid_source_filename(invalid_filename):
    service = EndToEndWorkflowOrchestrationService(
        integration_service=FakeIntegrationService()
    )

    with pytest.raises(EndToEndWorkflowOrchestrationError) as exc_info:
        service.execute({invalid_filename: SimpleNamespace(language="python")})

    assert exc_info.value.stage == "input_validation"


def test_execute_rejects_none_parsed_source():
    service = EndToEndWorkflowOrchestrationService(
        integration_service=FakeIntegrationService()
    )

    with pytest.raises(EndToEndWorkflowOrchestrationError) as exc_info:
        service.execute({"app.py": None})

    assert exc_info.value.stage == "input_validation"


def test_execute_wraps_integration_failure(parsed_sources):
    integration = FakeIntegrationService(error=RuntimeError("integration failed"))
    service = EndToEndWorkflowOrchestrationService(integration_service=integration)

    with pytest.raises(EndToEndWorkflowOrchestrationError) as exc_info:
        service.execute(parsed_sources)

    assert exc_info.value.stage == "advanced_intelligence_integration"
    assert "integration failed" in str(exc_info.value)


def test_execute_preserves_original_exception_as_cause(parsed_sources):
    original_error = RuntimeError("integration failed")
    service = EndToEndWorkflowOrchestrationService(
        integration_service=FakeIntegrationService(error=original_error)
    )

    with pytest.raises(EndToEndWorkflowOrchestrationError) as exc_info:
        service.execute(parsed_sources)

    assert exc_info.value.__cause__ is original_error


def test_execute_rejects_none_integration_result(parsed_sources):
    service = EndToEndWorkflowOrchestrationService(
        integration_service=FakeIntegrationService(result=None)
    )

    service.integration_service.result = None

    with pytest.raises(EndToEndWorkflowOrchestrationError) as exc_info:
        service.execute(parsed_sources)

    assert exc_info.value.stage == "advanced_intelligence_integration"


def test_result_contains_integration_result(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    result = orchestration_service.execute(parsed_sources)

    assert result.integration_result is integration_service.result


def test_result_exposes_investigation_result(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    result = orchestration_service.execute(parsed_sources)

    assert result.investigation_result is integration_service.result.investigation_result


def test_result_exposes_report(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    result = orchestration_service.execute(parsed_sources)

    assert result.report is integration_service.result.report


def test_result_exposes_evaluation(
    orchestration_service,
    integration_service,
    parsed_sources,
):
    result = orchestration_service.execute(parsed_sources)

    assert result.evaluation is integration_service.result.evaluation


def test_result_contains_completed_stages(
    orchestration_service,
    parsed_sources,
):
    result = orchestration_service.execute(parsed_sources)

    assert result.completed_stages == (
        "input_validation",
        "advanced_intelligence_integration",
        "workflow_completed",
    )


def test_result_contains_workflow_summary(
    orchestration_service,
    parsed_sources,
):
    result = orchestration_service.execute(parsed_sources)

    assert "2 files" in result.workflow_summary
    assert "completed successfully" in result.workflow_summary


def test_result_rejects_invalid_repository_file_count():
    with pytest.raises(ValueError):
        EndToEndWorkflowResult(
            repository_file_count=0,
            integration_result=object(),
            completed_stages=(
                "input_validation",
                "advanced_intelligence_integration",
                "workflow_completed",
            ),
            workflow_summary="Completed",
        )


def test_result_rejects_boolean_repository_file_count():
    with pytest.raises(ValueError):
        EndToEndWorkflowResult(
            repository_file_count=True,
            integration_result=object(),
            completed_stages=(
                "input_validation",
                "advanced_intelligence_integration",
                "workflow_completed",
            ),
            workflow_summary="Completed",
        )


def test_result_rejects_none_integration_result():
    with pytest.raises(ValueError):
        EndToEndWorkflowResult(
            repository_file_count=1,
            integration_result=None,
            completed_stages=(
                "input_validation",
                "advanced_intelligence_integration",
                "workflow_completed",
            ),
            workflow_summary="Completed",
        )


def test_result_rejects_non_tuple_completed_stages():
    with pytest.raises(ValueError):
        EndToEndWorkflowResult(
            repository_file_count=1,
            integration_result=object(),
            completed_stages=["workflow_completed"],
            workflow_summary="Completed",
        )


def test_result_rejects_invalid_stage_name():
    with pytest.raises(ValueError):
        EndToEndWorkflowResult(
            repository_file_count=1,
            integration_result=object(),
            completed_stages=(
                "input_validation",
                "",
                "workflow_completed",
            ),
            workflow_summary="Completed",
        )


def test_result_rejects_incorrect_stage_sequence():
    with pytest.raises(ValueError):
        EndToEndWorkflowResult(
            repository_file_count=1,
            integration_result=object(),
            completed_stages=("workflow_completed",),
            workflow_summary="Completed",
        )


def test_result_rejects_empty_workflow_summary():
    with pytest.raises(ValueError):
        EndToEndWorkflowResult(
            repository_file_count=1,
            integration_result=object(),
            completed_stages=(
                "input_validation",
                "advanced_intelligence_integration",
                "workflow_completed",
            ),
            workflow_summary=" ",
        )


def test_falsey_injected_service_is_not_replaced():
    class FalseyIntegrationService(FakeIntegrationService):
        def __bool__(self):
            return False

    integration = FalseyIntegrationService()
    service = EndToEndWorkflowOrchestrationService(
        integration_service=integration
    )

    assert service.integration_service is integration
