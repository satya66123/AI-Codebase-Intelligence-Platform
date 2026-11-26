
from contextlib import contextmanager
from types import SimpleNamespace

from appy.application.advanced_intelligence_ui_integration import (
    AdvancedIntelligenceUIIntegration,
)


class FakeUI:
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
        yield
        self.calls.append(("spinner_end", text))

    @contextmanager
    def expander(self, label, expanded=False):
        self.expanders.append((label, expanded))
        yield


class FakeApplicationService:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def create_successful_result():
    return SimpleNamespace(
        is_successful=True,
        message="Analysis completed successfully.",
        repository_file_count=4,
        report=SimpleNamespace(
            report_text="# Architecture Report"
        ),
        evaluation=SimpleNamespace(
            overall_score=95.0,
            overall_level="high",
            recommendations=("Improve module boundaries.",),
        ),
        investigation_result=SimpleNamespace(
            investigation_summary="Four files investigated."
        ),
        completed_stages=(
            "input_validation",
            "advanced_intelligence_integration",
            "workflow_completed",
        ),
    )


def test_existing_result_is_rendered_without_reexecution():
    ui = FakeUI(button_result=False)
    application_service = FakeApplicationService()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=application_service,
        ui=ui,
    )

    result = create_successful_result()

    returned = integration.render(
        parsed_sources={"appy.py": object()},
        existing_result=result,
    )

    assert returned is result
    assert application_service.calls == []
    assert ("success", "Analysis completed successfully.") in ui.calls


def test_existing_result_displays_repository_file_count():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    integration.render_result(create_successful_result())

    assert ("metric", "Repository files analyzed", 4) in ui.calls


def test_existing_result_displays_evaluation_score():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    integration.render_result(create_successful_result())

    assert ("metric", "Advanced analysis score", 95.0) in ui.calls


def test_existing_result_displays_architecture_report():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    integration.render_result(create_successful_result())

    assert ("Architecture Intelligence Report", True) in ui.expanders
    assert ("markdown", "# Architecture Report") in ui.calls


def test_existing_result_displays_investigation_summary():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    integration.render_result(create_successful_result())

    assert ("Investigation Summary", False) in ui.expanders
    assert (
        "write",
        "Four files investigated.",
    ) in ui.calls


def test_existing_result_displays_recommendations():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    integration.render_result(create_successful_result())

    assert ("Recommendations", False) in ui.expanders
    assert (
        "write",
        "- Improve module boundaries.",
    ) in ui.calls


def test_existing_result_displays_completed_stages():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    integration.render_result(create_successful_result())

    assert ("Completed Workflow Stages", False) in ui.expanders
    assert (
        "write",
        "- workflow_completed",
    ) in ui.calls


def test_invalid_existing_result_is_not_rendered():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    result = SimpleNamespace(is_successful=False)

    assert integration.render_result(result) is False
    assert not any(call[0] == "success" for call in ui.calls)


def test_render_returns_none_when_no_previous_result():
    ui = FakeUI(button_result=False)
    application_service = FakeApplicationService()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=application_service,
        ui=ui,
    )

    result = integration.render(
        parsed_sources={"appy.py": object()},
    )

    assert result is None
    assert application_service.calls == []


def test_successful_new_analysis_still_executes():
    ui = FakeUI(button_result=True)
    expected_result = create_successful_result()
    application_service = FakeApplicationService(expected_result)

    integration = AdvancedIntelligenceUIIntegration(
        application_service=application_service,
        ui=ui,
    )

    result = integration.render(
        parsed_sources={"appy.py": object()},
    )

    assert result is expected_result
    assert len(application_service.calls) == 1


def test_invalid_parsed_sources_are_rejected():
    ui = FakeUI()

    integration = AdvancedIntelligenceUIIntegration(
        application_service=FakeApplicationService(),
        ui=ui,
    )

    result = integration.render(parsed_sources=None)

    assert result is None
    assert any(
        call[0] == "error"
        and "mapping" in call[1]
        for call in ui.calls
    )
