
from types import SimpleNamespace

from appy.presentation import repository_discovery_view as view


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.messages = []
        self.clicked_buttons = set()
        self.inputs = {}

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

    def warning(self, value):
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


class FakeAdvancedIntelligenceUI:
    def __init__(self):
        self.calls = []

    def render(self, **kwargs):
        self.calls.append(kwargs)
        return None


def create_discovery_result():
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
                }
            ],
        },
    )


def create_loading_result():
    parsed_source = SimpleNamespace(
        language="Python",
        line_count=3,
    )

    return SimpleNamespace(
        selected_file_count=1,
        parsed_file_count=1,
        skipped_file_count=0,
        failed_file_count=0,
        language_counts={"Python": 1},
        parsed_sources={"main.py": parsed_source},
        source_files={"main.py": "def main():\n    return True\n"},
        failures=(),
    )


def setup_view(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(view, "st", fake)

    discovery_result = create_discovery_result()
    fake.session_state[view.SESSION_RESULT_KEY] = discovery_result

    discovery_service = SimpleNamespace(
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    return fake, discovery_result, discovery_service


def test_advanced_intelligence_receives_parsed_sources(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    loading_result = create_loading_result()
    fake.session_state[view.SESSION_SOURCE_RESULT_KEY] = loading_result

    advanced_ui = FakeAdvancedIntelligenceUI()

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=advanced_ui,
    )

    assert len(advanced_ui.calls) == 1
    assert (
        advanced_ui.calls[0]["parsed_sources"]
        == loading_result.parsed_sources
    )
    assert advanced_ui.calls[0]["source_files"] == ("main.py",)


def test_advanced_intelligence_is_not_called_without_parsed_sources(
    monkeypatch,
):
    fake, _, discovery_service = setup_view(monkeypatch)

    loading_result = create_loading_result()
    loading_result.parsed_sources = {}
    loading_result.parsed_file_count = 0

    fake.session_state[view.SESSION_SOURCE_RESULT_KEY] = loading_result

    advanced_ui = FakeAdvancedIntelligenceUI()

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=advanced_ui,
    )

    assert advanced_ui.calls == []
    assert any(
        "No source files were successfully parsed" in str(message)
        for message in fake.messages
    )


def test_advanced_intelligence_receives_filenames_without_losing_source_contents(
    monkeypatch,
):
    fake, _, discovery_service = setup_view(monkeypatch)

    loading_result = create_loading_result()
    fake.session_state[view.SESSION_SOURCE_RESULT_KEY] = loading_result

    advanced_ui = FakeAdvancedIntelligenceUI()

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=advanced_ui,
    )

    assert len(advanced_ui.calls) == 1

    # Advanced investigation receives an ordered iterable of filenames.
    assert advanced_ui.calls[0]["source_files"] == ("main.py",)

    # The original source contents remain available in the loading result.
    assert loading_result.source_files["main.py"] == (
        "def main():\n    return True\n"
    )


def test_existing_discovery_view_remains_available(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    view.render_repository_discovery_view(discovery_service)

    assert "Repository Discovery" in fake.messages
    assert "Repository Overview" in fake.messages


def test_advanced_integration_is_not_called_before_parsing(
    monkeypatch,
):
    fake, _, discovery_service = setup_view(monkeypatch)

    advanced_ui = FakeAdvancedIntelligenceUI()

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=advanced_ui,
    )

    assert advanced_ui.calls == []
