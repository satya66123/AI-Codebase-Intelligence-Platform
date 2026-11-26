
from types import SimpleNamespace

import pytest

from appy.presentation import repository_discovery_view as view


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.messages = []
        self.inputs = {}
        self.button_clicked = True

    def header(self, value):
        self.messages.append(value)

    def caption(self, value):
        self.messages.append(value)

    def text_input(self, label, **kwargs):
        return self.inputs.get(label, "")

    def button(self, label, **kwargs):
        return self.button_clicked

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


def test_discovery_view_without_repository(
    fake_streamlit,
):
    fake_streamlit.button_clicked = False

    service = SimpleNamespace()

    view.render_repository_discovery_view(service)

    assert "Repository Discovery" in fake_streamlit.messages
    assert any(
        "Enter a repository path" in str(message)
        for message in fake_streamlit.messages
    )


def test_discovery_view_runs_repository_discovery(
    fake_streamlit,
    sample_result,
):
    fake_streamlit.inputs["Local repository path"] = (
        "C:/projects/test_project"
    )

    service = SimpleNamespace(
        discover=lambda path: sample_result,
        search_files=lambda query: [],
        restore_result=lambda result: None,
    )

    view.render_repository_discovery_view(service)

    assert (
        fake_streamlit.session_state[
            view.SESSION_RESULT_KEY
        ] is sample_result
    )

    assert any(
        "Repository discovery completed" in str(message)
        for message in fake_streamlit.messages
    )


def test_discovery_view_rejects_empty_path(
    fake_streamlit,
):
    fake_streamlit.inputs["Local repository path"] = ""

    service = SimpleNamespace()

    view.render_repository_discovery_view(service)

    assert any(
        "Please enter a repository path" in str(message)
        for message in fake_streamlit.messages
    )


def test_discovery_view_handles_discovery_error(
    fake_streamlit,
):
    fake_streamlit.inputs["Local repository path"] = (
        "C:/invalid/repository"
    )

    def fail_discovery(path):
        raise ValueError("Repository not found")

    service = SimpleNamespace(
        discover=fail_discovery,
    )

    view.render_repository_discovery_view(service)

    assert any(
        "Repository discovery failed" in str(message)
        for message in fake_streamlit.messages
    )


def test_discovery_view_searches_files(
    fake_streamlit,
    sample_result,
):
    fake_streamlit.button_clicked = False
    fake_streamlit.session_state[
        view.SESSION_RESULT_KEY
    ] = sample_result

    fake_streamlit.inputs[
        "Search by filename, path, extension or language"
    ] = "Python"

    service = SimpleNamespace(
        search_files=lambda query: [
            {"name": "main.py", "language": "Python"}
        ],
        restore_result=lambda result: None,
    )

    view.render_repository_discovery_view(service)

    assert any(
        "Matching files: 1" in str(message)
        for message in fake_streamlit.messages
    )
