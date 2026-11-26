
from types import SimpleNamespace

from appy.presentation.code_quality_view import (
    SESSION_QUALITY_RESULT_KEY,
    render_code_quality_view,
)


class FakeUI:
    def __init__(self, clicked=False):
        self.clicked = clicked
        self.messages = []
        self.metrics = []
        self.tables = []
        self.json_values = []

    def header(self, value):
        self.messages.append(value)

    def caption(self, value):
        self.messages.append(value)

    def subheader(self, value):
        self.messages.append(value)

    def metric(self, label, value):
        self.metrics.append((label, value))

    def button(self, label, **kwargs):
        return self.clicked

    def success(self, value):
        self.messages.append(value)

    def warning(self, value):
        self.messages.append(value)

    def error(self, value):
        self.messages.append(value)

    def info(self, value):
        self.messages.append(value)

    def dataframe(self, value, **kwargs):
        self.tables.append(value)

    def json(self, value):
        self.json_values.append(value)


class FakeQualityService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def analyze(self, source_files):
        self.calls.append(source_files)

        if self.error:
            raise self.error

        return self.result


def create_result():
    finding = SimpleNamespace(
        code="LINE_TOO_LONG",
        severity=SimpleNamespace(value="warning"),
        category=SimpleNamespace(value="style"),
        file_path="appy.py",
        line=10,
        symbol="main",
        message="Line exceeds the configured maximum length.",
    )

    file_result = SimpleNamespace(
        file_path="appy.py",
        score=90.0,
        lines_of_code=20,
        findings=(finding,),
    )

    return SimpleNamespace(
        total_files=2,
        analyzed_files=1,
        skipped_files=1,
        total_lines_of_code=20,
        score=90.0,
        error_count=0,
        warning_count=1,
        info_count=0,
        healthy=True,
        file_results=(file_result,),
        findings=(finding,),
        findings_by_severity={"warning": 1},
        findings_by_category={"style": 1},
    )


def test_empty_source_files_displays_information():
    ui = FakeUI()
    state = {}
    service = FakeQualityService()

    render_code_quality_view(
        source_files={},
        service=service,
        ui=ui,
        session_state=state,
    )

    assert any(
        "load source files" in message.lower()
        for message in ui.messages
    )
    assert service.calls == []


def test_invalid_source_files_are_rejected():
    ui = FakeUI()
    service = FakeQualityService()

    render_code_quality_view(
        source_files=None,
        service=service,
        ui=ui,
        session_state={},
    )

    assert any(
        "mapping" in message.lower()
        for message in ui.messages
    )
    assert service.calls == []


def test_analysis_runs_when_button_is_clicked():
    ui = FakeUI(clicked=True)
    state = {}
    result = create_result()
    service = FakeQualityService(result=result)

    source_files = {"appy.py": "print('hello')"}

    render_code_quality_view(
        source_files=source_files,
        service=service,
        ui=ui,
        session_state=state,
    )

    assert service.calls == [source_files]
    assert state[SESSION_QUALITY_RESULT_KEY] is result


def test_successful_analysis_displays_summary():
    ui = FakeUI(clicked=True)
    state = {}
    service = FakeQualityService(result=create_result())

    render_code_quality_view(
        source_files={"appy.py": "print('hello')"},
        service=service,
        ui=ui,
        session_state=state,
    )

    assert ("Quality Score", "90.0/100") in ui.metrics
    assert ("Analyzed Files", 1) in ui.metrics
    assert ("Warnings", 1) in ui.metrics


def test_analysis_result_is_preserved_without_new_execution():
    ui = FakeUI(clicked=False)
    result = create_result()
    state = {SESSION_QUALITY_RESULT_KEY: result}
    service = FakeQualityService()

    render_code_quality_view(
        source_files={"appy.py": "print('hello')"},
        service=service,
        ui=ui,
        session_state=state,
    )

    assert service.calls == []
    assert ("Quality Score", "90.0/100") in ui.metrics


def test_file_quality_results_are_displayed():
    ui = FakeUI(clicked=False)
    state = {SESSION_QUALITY_RESULT_KEY: create_result()}

    render_code_quality_view(
        source_files={"appy.py": "print('hello')"},
        service=FakeQualityService(),
        ui=ui,
        session_state=state,
    )

    assert any(
        row["File"] == "appy.py"
        for table in ui.tables
        for row in table
    )


def test_detailed_findings_are_displayed():
    ui = FakeUI(clicked=False)
    state = {SESSION_QUALITY_RESULT_KEY: create_result()}

    render_code_quality_view(
        source_files={"appy.py": "print('hello')"},
        service=FakeQualityService(),
        ui=ui,
        session_state=state,
    )

    finding_rows = [
        row
        for table in ui.tables
        for row in table
        if "Code" in row
    ]

    assert any(
        row["Code"] == "LINE_TOO_LONG"
        for row in finding_rows
    )


def test_analysis_exception_is_displayed():
    ui = FakeUI(clicked=True)
    service = FakeQualityService(
        error=RuntimeError("Analysis failed")
    )

    render_code_quality_view(
        source_files={"appy.py": "print('hello')"},
        service=service,
        ui=ui,
        session_state={},
    )

    assert any(
        "Analysis failed" in message
        for message in ui.messages
    )


def test_existing_result_is_not_removed_after_rerun():
    ui = FakeUI(clicked=False)
    result = create_result()
    state = {SESSION_QUALITY_RESULT_KEY: result}

    render_code_quality_view(
        source_files={"appy.py": "print('hello')"},
        service=FakeQualityService(),
        ui=ui,
        session_state=state,
    )

    assert state[SESSION_QUALITY_RESULT_KEY] is result


def test_quality_summary_displays_category_and_severity():
    ui = FakeUI(clicked=False)
    state = {SESSION_QUALITY_RESULT_KEY: create_result()}

    render_code_quality_view(
        source_files={"appy.py": "print('hello')"},
        service=FakeQualityService(),
        ui=ui,
        session_state=state,
    )

    assert {"warning": 1} in ui.json_values
    assert {"style": 1} in ui.json_values
