
"""Tests for advanced intelligence Streamlit UI integration."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from appy.application.advanced_intelligence_ui_integration import (
    AdvancedIntelligenceUIIntegration,
    AdvancedIntelligenceUIIntegrationError,
)


class FakeUI:
    """Minimal Streamlit-compatible test double."""

    def __init__(self, button_result=False):
        self.button_result = button_result
        self.calls = []
        self.expanders = []

    def subheader(self, text):
        self.calls.append(("subheader", text))

    def caption(self, text):
        self.calls.append(("caption", text))

    def button(self, label, key=None):
        self.calls.append(("button", label, key))
        return self.button_result

    def info(self, text):
        self.calls.append(("info", text))

    def error(self, text):
        self.calls.append(("error", text))

    def success(self, text):
        self.calls.append(("success", text))

    def metric(self, label, value):
        self.calls.append(("metric", label, value))

    def write(self, text):
        self.calls.append(("write", text))

    def markdown(self, text):
        self.calls.append(("markdown", text))

    @contextmanager
    def spinner(self, text):
        self.calls.append(("spinner_start", text))
        try:
            yield
        finally:
            self.calls.append(("spinner_end", text))

    @contextmanager
    def expander(self, label, expanded=False):
        self.expanders.append((label, expanded))
        self.calls.append(("expander_start", label, expanded))
        try:
            yield
        finally:
            self.calls.append(("expander_end", label, expanded))


class FakeApplicationService:
    """Test double for the final application integration service."""

    def __init__(self, result=None, error=None):
        self.result = result or SimpleNamespace(
            is_successful=True,
            message="Analysis completed successfully.",
            repository_file_count=2,
            report=SimpleNamespace(report_text="# Architecture Report"),
            evaluation=SimpleNamespace(
                overall_score=95.0,
                overall_level="high",
                recommendations=("Improve module boundaries.",),
            ),
            investigation_result=SimpleNamespace(
                investigation_summary="Two files investigated."
            ),
            completed_stages=("input_validation", "workflow_completed"),
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
def application_service():
    return FakeApplicationService()


@pytest.fixture
def ui():
    return FakeUI(button_result=True)


@pytest.fixture
def integration(ui, application_service):
    return AdvancedIntelligenceUIIntegration(
        application_service=application_service,
        ui=ui,
    )


def test_constructor_accepts_injected_application_service(application_service, ui):
    component = AdvancedIntelligenceUIIntegration(
        application_service=application_service,
        ui=ui,
    )

    assert component.application_service is application_service
    assert component.ui is ui


def test_constructor_creates_default_application_service(ui):
    component = AdvancedIntelligenceUIIntegration(ui=ui)

    assert component.application_service is not None


def test_render_displays_page_heading(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("subheader", "Advanced Codebase Intelligence") in ui.calls


def test_render_displays_page_description(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert any(call[0] == "caption" for call in ui.calls)


def test_render_displays_analysis_button(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert (
        "button",
        "Run Advanced Intelligence Analysis",
        "advanced_intelligence_analysis",
    ) in ui.calls


def test_render_does_not_execute_when_button_not_clicked(
    application_service,
    parsed_sources,
):
    ui = FakeUI(button_result=False)
    component = AdvancedIntelligenceUIIntegration(
        application_service=application_service,
        ui=ui,
    )

    result = component.render(parsed_sources)

    assert result is None
    assert application_service.calls == []


def test_render_executes_when_button_clicked(integration, parsed_sources, application_service):
    integration.render(parsed_sources)

    assert len(application_service.calls) == 1


def test_render_returns_application_result(integration, parsed_sources, application_service):
    result = integration.render(parsed_sources)

    assert result is application_service.result


def test_render_forwards_parsed_sources(
    integration,
    parsed_sources,
    application_service,
):
    integration.render(parsed_sources)

    assert application_service.calls[0]["parsed_sources"] is parsed_sources


def test_render_forwards_source_files(
    integration,
    parsed_sources,
    application_service,
):
    source_files = {"appy.py": "print('hello')"}

    integration.render(parsed_sources, source_files=source_files)

    assert application_service.calls[0]["source_files"] is source_files


def test_render_forwards_code_entities(
    integration,
    parsed_sources,
    application_service,
):
    entities = (SimpleNamespace(name="main"),)

    integration.render(parsed_sources, code_entities=entities)

    assert application_service.calls[0]["code_entities"] is entities


def test_render_forwards_dependencies(
    integration,
    parsed_sources,
    application_service,
):
    dependencies = (SimpleNamespace(source="appy.py"),)

    integration.render(parsed_sources, dependencies=dependencies)

    assert application_service.calls[0]["dependencies"] is dependencies


def test_render_forwards_call_graphs(
    integration,
    parsed_sources,
    application_service,
):
    call_graphs = (SimpleNamespace(name="main"),)

    integration.render(parsed_sources, call_graphs=call_graphs)

    assert application_service.calls[0]["call_graphs"] is call_graphs


def test_render_forwards_entry_points(
    integration,
    parsed_sources,
    application_service,
):
    entry_points = ("appy.main",)

    integration.render(parsed_sources, entry_points=entry_points)

    assert application_service.calls[0]["entry_points"] is entry_points


def test_render_forwards_max_depth(
    integration,
    parsed_sources,
    application_service,
):
    integration.render(parsed_sources, max_depth=15)

    assert application_service.calls[0]["max_depth"] == 15


def test_render_forwards_change_impact_result(
    integration,
    parsed_sources,
    application_service,
):
    impact = SimpleNamespace(name="change-impact")

    integration.render(parsed_sources, change_impact_result=impact)

    assert application_service.calls[0]["change_impact_result"] is impact


def test_render_forwards_direct_indirect_impact_result(
    integration,
    parsed_sources,
    application_service,
):
    impact = SimpleNamespace(name="direct-indirect-impact")

    integration.render(parsed_sources, direct_indirect_impact_result=impact)

    assert (
        application_service.calls[0]["direct_indirect_impact_result"]
        is impact
    )


@pytest.mark.parametrize(
    "invalid_sources",
    [None, (), [], "appy.py", 123],
)
def test_render_rejects_non_mapping_sources(integration, invalid_sources, ui):
    result = integration.render(invalid_sources)

    assert result is None
    assert any(call[0] == "error" for call in ui.calls)


def test_render_handles_empty_sources(integration, ui):
    result = integration.render({})

    assert result is None
    assert any(
        call[0] == "info" and "Load and parse" in call[1]
        for call in ui.calls
    )


def test_render_does_not_execute_with_invalid_sources(
    application_service,
    ui,
):
    component = AdvancedIntelligenceUIIntegration(
        application_service=application_service,
        ui=ui,
    )

    component.render(None)

    assert application_service.calls == []


def test_render_displays_spinner(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert any(call[0] == "spinner_start" for call in ui.calls)
    assert any(call[0] == "spinner_end" for call in ui.calls)


def test_render_displays_success_message(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert any(call[0] == "success" for call in ui.calls)


def test_render_displays_repository_file_metric(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("metric", "Repository files analyzed", 2) in ui.calls


def test_render_displays_evaluation_score(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("metric", "Advanced analysis score", 95.0) in ui.calls


def test_render_displays_evaluation_level(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("write", "Evaluation level: high") in ui.calls


def test_render_displays_architecture_report(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("markdown", "# Architecture Report") in ui.calls


def test_render_displays_investigation_summary(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("write", "Two files investigated.") in ui.calls


def test_render_displays_recommendations(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("write", "- Improve module boundaries.") in ui.calls


def test_render_displays_completed_stages(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("write", "- input_validation") in ui.calls
    assert ("write", "- workflow_completed") in ui.calls


def test_render_creates_report_expander(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("Architecture Intelligence Report", True) in ui.expanders


def test_render_creates_investigation_expander(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("Investigation Summary", False) in ui.expanders


def test_render_creates_recommendations_expander(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("Recommendations", False) in ui.expanders


def test_render_creates_completed_stages_expander(integration, parsed_sources, ui):
    integration.render(parsed_sources)

    assert ("Completed Workflow Stages", False) in ui.expanders


def test_render_handles_application_service_failure(
    parsed_sources,
    ui,
):
    component = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(
            error=RuntimeError("service failure")
        ),
        ui=ui,
    )

    result = component.render(parsed_sources)

    assert result is None
    assert any(
        call[0] == "error" and "service failure" in call[1]
        for call in ui.calls
    )


def test_render_handles_unsuccessful_application_result(parsed_sources, ui):
    result = SimpleNamespace(is_successful=False)
    component = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(result=result),
        ui=ui,
    )

    returned = component.render(parsed_sources)

    assert returned is None
    assert any(
        call[0] == "error" and "did not complete" in call[1]
        for call in ui.calls
    )


def test_render_handles_none_application_result(parsed_sources, ui):
    component = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(result=None),
        ui=ui,
    )
    component.application_service.result = None

    returned = component.render(parsed_sources)

    assert returned is None
    assert any(call[0] == "error" for call in ui.calls)


def test_render_supports_custom_button_label_and_key(
    integration,
    parsed_sources,
    ui,
):
    integration.render(
        parsed_sources,
        button_label="Analyze Repository",
        button_key="custom_analysis",
    )

    assert (
        "button",
        "Analyze Repository",
        "custom_analysis",
    ) in ui.calls


def test_render_handles_missing_optional_report_and_evaluation(parsed_sources, ui):
    result = SimpleNamespace(
        is_successful=True,
        message="Completed",
        repository_file_count=1,
        report=None,
        evaluation=None,
        investigation_result=None,
        completed_stages=(),
    )
    component = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(result=result),
        ui=ui,
    )

    returned = component.render(parsed_sources)

    assert returned is result
    assert ("success", "Completed") in ui.calls


def test_falsey_injected_service_is_not_replaced(ui):
    class FalseyApplicationService(FakeApplicationService):
        def __bool__(self):
            return False

    service = FalseyApplicationService()
    component = AdvancedIntelligenceUIIntegration(
        application_service=service,
        ui=ui,
    )

    assert component.application_service is service


def test_falsey_injected_ui_is_not_replaced():
    class FalseyUI(FakeUI):
        def __bool__(self):
            return False

    ui = FalseyUI(button_result=False)
    component = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    assert component.ui is ui
