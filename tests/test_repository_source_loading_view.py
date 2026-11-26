
from types import SimpleNamespace

import pytest

from appy.presentation import repository_discovery_view as view


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.messages = []
        self.inputs = {}
        self.clicked_buttons = set()

    def header(self, value):
        self.messages.append(value)

    def caption(self, value):
        self.messages.append(value)

    def text_input(self, label, **kwargs):
        return self.inputs.get(label, "")

    def button(self, label, **kwargs):
        return kwargs.get("key") in self.clicked_buttons

    def success(self, value):
        self.messages.append(value)

    def error(self, value):
        self.messages.append(value)

    def info(self, value):
        self.messages.append(value)

    def subheader(self, value):
        self.messages.append(value)

    def write(self, *args):
        self.messages.append(args)

    def metric(self, label, value):
        self.messages.append((label, value))

    def json(self, value):
        self.messages.append(value)

    def code(self, value, **kwargs):
        self.messages.append(value)

    def dataframe(self, value, **kwargs):
        self.messages.append(value)

    def divider(self):
        self.messages.append("divider")


@pytest.fixture
def fake_streamlit(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(view, "st", fake)
    return fake


@pytest.fixture
def sample_result():
    return SimpleNamespace(
        repository=SimpleNamespace(
            name="test_project",
            root="C:/projects/test_project",
        ),
        repository_map="test_project\n└── main.py",
        metadata={
            "total_files": 1,
            "total_directories": 0,
            "total_size_bytes": 20,
            "languages": {"Python": 1},
            "files": [
                {
                    "name": "main.py",
                    "relative_path": "main.py",
                    "extension": ".py",
                    "language": "Python",
                    "size_bytes": 20,
                    "modified_time": "2026-11-24T10:00:00",
                }
            ],
        },
    )


@pytest.fixture
def loading_result():
    return SimpleNamespace(
        selected_file_count=1,
        parsed_file_count=1,
        skipped_file_count=0,
        failed_file_count=0,
        language_counts={"Python": 1},
        parsed_sources={
            "main.py": SimpleNamespace(
                language="Python",
                line_count=3,
            )
        },
        source_files={
            "main.py": "def main():\n    return True"
        },
        failures=(),
    )


def test_source_loading_button_calls_service(
    fake_streamlit,
    sample_result,
    loading_result,
):
    fake_streamlit.session_state[view.SESSION_RESULT_KEY] = sample_result
    fake_streamlit.clicked_buttons.add("load_parse_source_files_button")

    calls = []

    discovery_service = SimpleNamespace(
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    source_service = SimpleNamespace(
        load_and_parse=lambda **kwargs: (
            calls.append(kwargs) or loading_result
        )
    )

    view.render_repository_discovery_view(
        discovery_service,
        source_service,
    )

    assert len(calls) == 1
    assert calls[0]["repository_path"] == sample_result.repository.root
    assert calls[0]["file_metadata"] == sample_result.metadata["files"]
    assert (
        fake_streamlit.session_state[view.SESSION_SOURCE_RESULT_KEY]
        is loading_result
    )


def test_source_loading_summary_is_displayed(
    fake_streamlit,
    sample_result,
    loading_result,
):
    fake_streamlit.session_state[view.SESSION_RESULT_KEY] = sample_result
    fake_streamlit.session_state[
        view.SESSION_SOURCE_RESULT_KEY
    ] = loading_result

    discovery_service = SimpleNamespace(
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    source_service = SimpleNamespace()

    view.render_repository_discovery_view(
        discovery_service,
        source_service,
    )

    assert "Source Parsing Summary" in fake_streamlit.messages
    assert ("Selected Source Files", 1) in fake_streamlit.messages
    assert ("Successfully Parsed", 1) in fake_streamlit.messages


def test_source_loading_errors_are_displayed(
    fake_streamlit,
    sample_result,
):
    fake_streamlit.session_state[view.SESSION_RESULT_KEY] = sample_result
    fake_streamlit.clicked_buttons.add("load_parse_source_files_button")

    discovery_service = SimpleNamespace(
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    def fail_loading(**kwargs):
        raise RuntimeError("Parsing failed")

    source_service = SimpleNamespace(
        load_and_parse=fail_loading
    )

    view.render_repository_discovery_view(
        discovery_service,
        source_service,
    )

    assert any(
        "Source loading failed" in str(message)
        for message in fake_streamlit.messages
    )


def test_discovery_view_remains_compatible_without_loading_service(
    fake_streamlit,
    sample_result,
):
    fake_streamlit.session_state[view.SESSION_RESULT_KEY] = sample_result

    discovery_service = SimpleNamespace(
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    view.render_repository_discovery_view(discovery_service)

    assert "Repository Discovery" in fake_streamlit.messages


def test_new_discovery_clears_previous_source_result(
    fake_streamlit,
    sample_result,
):
    fake_streamlit.inputs["Local repository path"] = "C:/projects/test_project"
    fake_streamlit.clicked_buttons.add("discover_repository_button")
    fake_streamlit.session_state[
        view.SESSION_SOURCE_RESULT_KEY
    ] = object()

    discovery_service = SimpleNamespace(
        discover=lambda path: sample_result,
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    view.render_repository_discovery_view(
        discovery_service,
        SimpleNamespace(),
    )

    assert view.SESSION_SOURCE_RESULT_KEY not in fake_streamlit.session_state
