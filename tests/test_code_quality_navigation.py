
from types import SimpleNamespace

import pytest

from appy.presentation.pages import home

from appy.presentation.repository_discovery_view import (
    render_repository_discovery_view,
)

from appy.presentation.code_quality_view import (
    render_code_quality_view,
)


class FakeSidebar:
    def __init__(self, selected_page="Home"):
        self.selected_page = selected_page
        self.messages = []
        self.options = []

    def title(self, value):
        self.messages.append(value)

    def radio(self, label, options):
        assert label == "Select Page"
        self.options = list(options)
        assert self.selected_page in self.options
        return self.selected_page


class FakeStreamlit:
    def __init__(self, selected_page="Home"):
        self.sidebar = FakeSidebar(selected_page)
        self.session_state = {}
        self.messages = []
        self.selectbox_calls = []

    def title(self, value):
        self.messages.append(value)

    def markdown(self, value):
        self.messages.append(value)

    def subheader(self, value):
        self.messages.append(value)

    def header(self, value):
        self.messages.append(value)

    def info(self, value):
        self.messages.append(value)

    def selectbox(self, label, options):
        options = list(options)
        self.selectbox_calls.append((label, options))
        return options[0] if options else None


@pytest.fixture
def fake_streamlit(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(home, "st", fake)
    return fake


class FakeContainer:
    def __init__(self):
        self.provider_model_service = SimpleNamespace(
            get_providers=lambda: ["Ollama", "OpenAI"],
            get_models=lambda provider: [
                SimpleNamespace(name="qwen2.5:1.5b"),
                SimpleNamespace(name="gpt-4o"),
            ],
        )

        self.discovery_service = object()
        self.source_loading_service = object()
        self.code_quality_service = object()

        self.calls = []

    def create_provider_model_service(self):
        self.calls.append("provider_model")
        return self.provider_model_service

    def create_repository_discovery_integration_service(self):
        self.calls.append("repository_discovery")
        return self.discovery_service

    def create_repository_source_loading_service(self):
        self.calls.append("source_loading")
        return self.source_loading_service

    def create_code_quality_analysis_service(self):
        self.calls.append("code_quality")
        return self.code_quality_service


def test_navigation_displays_all_three_pages(
    fake_streamlit,
    monkeypatch,
):
    container = FakeContainer()

    monkeypatch.setattr(
        home,
        "render_home",
        lambda selected_container: None,
    )

    home.render(container)

    assert fake_streamlit.sidebar.messages == ["Navigation"]

    assert fake_streamlit.sidebar.options == [
        "Home",
        "Repository Discovery",
        "Code Quality Analysis",
    ]


def test_home_navigation_calls_home_renderer(
    fake_streamlit,
    monkeypatch,
):
    container = FakeContainer()
    calls = []

    monkeypatch.setattr(
        home,
        "render_home",
        lambda selected_container: calls.append(selected_container),
    )

    fake_streamlit.sidebar.selected_page = "Home"

    home.render(container)

    assert calls == [container]


def test_repository_discovery_navigation_calls_renderer(
    fake_streamlit,
    monkeypatch,
):
    container = FakeContainer()
    calls = []

    monkeypatch.setattr(
        home,
        "render_repository_discovery",
        lambda selected_container: calls.append(selected_container),
    )

    fake_streamlit.sidebar.selected_page = "Repository Discovery"

    home.render(container)

    assert calls == [container]


def test_code_quality_navigation_calls_renderer(
    fake_streamlit,
    monkeypatch,
):
    container = FakeContainer()
    calls = []

    monkeypatch.setattr(
        home,
        "render_code_quality",
        lambda selected_container: calls.append(selected_container),
    )

    fake_streamlit.sidebar.selected_page = "Code Quality Analysis"

    home.render(container)

    assert calls == [container]


def test_home_page_loads_provider_and_model_options(
    fake_streamlit,
):
    container = FakeContainer()

    home.render_home(container)

    assert "provider_model" in container.calls

    assert fake_streamlit.selectbox_calls == [
        ("Select Provider", ["Ollama", "OpenAI"]),
        ("Select Model", ["qwen2.5:1.5b", "gpt-4o"]),
    ]


def test_repository_discovery_creates_required_services(
    fake_streamlit,
    monkeypatch,
):
    container = FakeContainer()
    calls = []

    monkeypatch.setattr(
        home,
        render_repository_discovery_view.__name__,
        lambda discovery, source: calls.append((discovery, source)),
    )

    home.render_repository_discovery(container)

    assert "repository_discovery" in container.calls
    assert "source_loading" in container.calls

    assert calls == [
        (
            container.discovery_service,
            container.source_loading_service,
        )
    ]


def test_code_quality_requires_loaded_source_files(
    fake_streamlit,
):
    container = FakeContainer()

    home.render_code_quality(container)

    assert "code_quality" not in container.calls

    assert any(
        "Please discover a repository" in str(message)
        for message in fake_streamlit.messages
    )


def test_code_quality_uses_loaded_source_files(
    fake_streamlit,
    monkeypatch,
):
    container = FakeContainer()

    source_files = {
        "main.py": "def main():\n    return True",
    }

    loading_result = SimpleNamespace(
        source_files=source_files,
    )

    fake_streamlit.session_state[
        home.SESSION_SOURCE_RESULT_KEY
    ] = loading_result

    calls = []

    monkeypatch.setattr(
        home,
        render_code_quality_view.__name__,
        lambda **kwargs: calls.append(kwargs),
    )

    home.render_code_quality(container)

    assert "code_quality" in container.calls

    assert calls == [
        {
            "source_files": source_files,
            "service": container.code_quality_service,
        }
    ]
