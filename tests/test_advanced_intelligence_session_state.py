
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


class FakeAdvancedIntegration:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def render(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


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
    return SimpleNamespace(
        selected_file_count=2,
        parsed_file_count=2,
        skipped_file_count=0,
        failed_file_count=0,
        language_counts={"Python": 2},
        parsed_sources={
            "appy.py": SimpleNamespace(
                language="Python",
                line_count=3,
            ),
            "service.py": SimpleNamespace(
                language="Python",
                line_count=5,
            ),
        },
        source_files={
            "appy.py": "def main():\n    return True\n",
            "service.py": "class Service:\n    pass\n",
        },
        failures=(),
    )


def create_successful_analysis():
    return SimpleNamespace(
        is_successful=True,
        message="Analysis completed.",
    )


def setup_view(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(view, "st", fake)

    discovery_result = create_discovery_result()
    fake.session_state[view.SESSION_RESULT_KEY] = discovery_result
    fake.session_state[view.SESSION_SOURCE_RESULT_KEY] = (
        create_loading_result()
    )

    discovery_service = SimpleNamespace(
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    return fake, discovery_result, discovery_service


def test_successful_analysis_is_saved_in_session_state(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    analysis_result = create_successful_analysis()
    integration = FakeAdvancedIntegration(analysis_result)

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    assert (
        fake.session_state[view.SESSION_ADVANCED_RESULT_KEY]
        is analysis_result
    )


def test_existing_analysis_result_is_passed_back_to_integration(
    monkeypatch,
):
    fake, _, discovery_service = setup_view(monkeypatch)

    existing_result = create_successful_analysis()
    fake.session_state[view.SESSION_ADVANCED_RESULT_KEY] = existing_result

    integration = FakeAdvancedIntegration(existing_result)

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    assert len(integration.calls) == 1
    assert integration.calls[0]["existing_result"] is existing_result


def test_failed_analysis_is_not_saved(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    failed_result = SimpleNamespace(is_successful=False)
    integration = FakeAdvancedIntegration(failed_result)

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    assert view.SESSION_ADVANCED_RESULT_KEY not in fake.session_state


def test_new_repository_discovery_clears_old_analysis(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(view, "st", fake)

    fake.inputs["Local repository path"] = "C:/projects/new_project"
    fake.clicked_buttons.add("discover_repository_button")

    fake.session_state[view.SESSION_ADVANCED_RESULT_KEY] = (
        create_successful_analysis()
    )
    fake.session_state[view.SESSION_SOURCE_RESULT_KEY] = (
        create_loading_result()
    )

    discovery_result = create_discovery_result()

    discovery_service = SimpleNamespace(
        discover=lambda path: discovery_result,
        restore_result=lambda result: None,
        search_files=lambda query: [],
    )

    view.render_repository_discovery_view(discovery_service)

    assert view.SESSION_ADVANCED_RESULT_KEY not in fake.session_state
    assert view.SESSION_SOURCE_RESULT_KEY not in fake.session_state


def test_reloading_sources_clears_previous_analysis(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    fake.clicked_buttons.add("load_parse_source_files_button")
    fake.session_state[view.SESSION_ADVANCED_RESULT_KEY] = (
        create_successful_analysis()
    )

    new_loading_result = create_loading_result()

    source_service = SimpleNamespace(
        load_and_parse=lambda **kwargs: new_loading_result
    )

    integration = FakeAdvancedIntegration()

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=source_service,
        advanced_intelligence_ui=integration,
    )

    assert view.SESSION_ADVANCED_RESULT_KEY not in fake.session_state
    assert (
        fake.session_state[view.SESSION_SOURCE_RESULT_KEY]
        is new_loading_result
    )


def test_no_analysis_result_is_saved_when_analysis_returns_none(
    monkeypatch,
):
    fake, _, discovery_service = setup_view(monkeypatch)

    integration = FakeAdvancedIntegration(None)

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    assert view.SESSION_ADVANCED_RESULT_KEY not in fake.session_state


def test_advanced_analysis_receives_parsed_sources(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    loading_result = fake.session_state[view.SESSION_SOURCE_RESULT_KEY]
    integration = FakeAdvancedIntegration(create_successful_analysis())

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    assert (
        integration.calls[0]["parsed_sources"]
        is loading_result.parsed_sources
    )


def test_advanced_analysis_is_not_called_without_parsed_sources(
    monkeypatch,
):
    fake, _, discovery_service = setup_view(monkeypatch)

    loading_result = fake.session_state[view.SESSION_SOURCE_RESULT_KEY]
    loading_result.parsed_sources = {}

    integration = FakeAdvancedIntegration()

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    assert integration.calls == []
    assert view.SESSION_ADVANCED_RESULT_KEY not in fake.session_state


def test_advanced_analysis_receives_ordered_filename_tuple(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    loading_result = fake.session_state[view.SESSION_SOURCE_RESULT_KEY]
    integration = FakeAdvancedIntegration(create_successful_analysis())

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    source_files = integration.calls[0]["source_files"]

    assert isinstance(source_files, tuple)
    assert source_files == ("appy.py", "service.py")


def test_source_contents_are_not_passed_as_source_filenames(monkeypatch):
    fake, _, discovery_service = setup_view(monkeypatch)

    loading_result = fake.session_state[view.SESSION_SOURCE_RESULT_KEY]
    integration = FakeAdvancedIntegration(create_successful_analysis())

    view.render_repository_discovery_view(
        discovery_service,
        source_loading_service=SimpleNamespace(),
        advanced_intelligence_ui=integration,
    )

    assert integration.calls[0]["source_files"] == (
        "appy.py",
        "service.py",
    )
    assert integration.calls[0]["source_files"] != (
        loading_result.source_files
    )
