
from types import SimpleNamespace

import pytest

from appy.application.advanced_code_investigation_agent import (
    AdvancedCodeInvestigationAgent,
    AdvancedCodeInvestigationError,
    AdvancedCodeInvestigationResult,
)


class FakeService:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else SimpleNamespace()
        self.error = error
        self.calls = []

    def analyze(self, **kwargs):
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        return self.result


@pytest.fixture
def parsed_sources():
    return {
        "main.py": SimpleNamespace(
            filename="main.py",
            language="python",
            tree=object(),
        ),
        "services/user.py": SimpleNamespace(
            filename="services/user.py",
            language="python",
            tree=object(),
        ),
    }


@pytest.fixture
def services():
    return {
        "architecture": FakeService(
            SimpleNamespace(patterns_detected=2, findings=("layered",))
        ),
        "responsibility": FakeService(
            SimpleNamespace(classified_modules=2, findings=("api",))
        ),
        "code_flow": FakeService(
            SimpleNamespace(has_execution_flows=True)
        ),
        "execution": FakeService(
            SimpleNamespace(has_execution_paths=True)
        ),
        "cross_module": FakeService(
            SimpleNamespace(has_cross_module_relationships=True)
        ),
        "data_flow": FakeService(
            (
                SimpleNamespace(
                    file_path="main.py",
                    analyzed=True,
                ),
                SimpleNamespace(
                    file_path="services/user.py",
                    analyzed=True,
                ),
            )
        ),
    }


@pytest.fixture
def agent(services):
    return AdvancedCodeInvestigationAgent(
        architecture_service=services["architecture"],
        responsibility_service=services["responsibility"],
        code_flow_service=services["code_flow"],
        execution_flow_service=services["execution"],
        cross_module_service=services["cross_module"],
        data_flow_service=services["data_flow"],
    )


def test_investigate_returns_unified_result(agent, parsed_sources):
    result = agent.investigate(parsed_sources)

    assert isinstance(result, AdvancedCodeInvestigationResult)
    assert result.total_files == 2
    assert result.analyzed_files == 2
    assert result.skipped_files == 0


def test_investigate_preserves_each_service_result(agent, parsed_sources, services):
    result = agent.investigate(parsed_sources)

    assert result.architecture_patterns is services["architecture"].result
    assert result.module_responsibilities is services["responsibility"].result
    assert result.code_flow is services["code_flow"].result
    assert result.execution_flow is services["execution"].result
    assert (
        result.cross_module_relationships
        is services["cross_module"].result
    )
    assert result.data_flow is services["data_flow"].result


def test_runs_all_six_analysis_services(agent, parsed_sources, services):
    agent.investigate(parsed_sources)

    for service in services.values():
        assert len(service.calls) == 1


def test_source_files_are_inferred_from_parsed_sources(
    agent,
    parsed_sources,
    services,
):
    agent.investigate(parsed_sources)

    assert services["architecture"].calls[0]["source_files"] == (
        "main.py",
        "services/user.py",
    )


def test_accepts_explicit_source_files(agent, parsed_sources, services):
    agent.investigate(
        parsed_sources,
        source_files=(
            "services/user.py",
            "main.py",
        ),
    )

    assert services["responsibility"].calls[0]["source_files"] == (
        "main.py",
        "services/user.py",
    )


def test_passes_code_entities_and_dependencies(agent, parsed_sources, services):
    entities = (SimpleNamespace(name="UserService"),)
    dependencies = (SimpleNamespace(source_file="main.py"),)
    call_graphs = (SimpleNamespace(filename="main.py", total_calls=2),)

    agent.investigate(
        parsed_sources,
        code_entities=entities,
        dependencies=dependencies,
        call_graphs=call_graphs,
    )

    architecture_call = services["architecture"].calls[0]

    assert architecture_call["code_entities"] == entities
    assert architecture_call["dependencies"] == dependencies
    assert architecture_call["call_graphs"] == call_graphs


def test_passes_entry_points_and_max_depth(agent, parsed_sources, services):
    agent.investigate(
        parsed_sources,
        entry_points=("main.main",),
        max_depth=5,
    )

    assert services["code_flow"].calls[0]["entry_points"] == (
        "main.main",
    )
    assert services["code_flow"].calls[0]["max_depth"] == 5

    assert services["execution"].calls[0]["entry_points"] == (
        "main.main",
    )
    assert services["execution"].calls[0]["max_depth"] == 5


def test_data_flow_receives_parsed_source_values(agent, parsed_sources, services):
    agent.investigate(parsed_sources)

    assert services["data_flow"].calls[0]["parsed_sources"] == tuple(
        parsed_sources.values()
    )


def test_summary_contains_all_analysis_stages(agent, parsed_sources):
    result = agent.investigate(parsed_sources)

    assert len(result.investigation_summary) == 6
    assert any(
        "Architecture patterns" in item
        for item in result.investigation_summary
    )
    assert any(
        "Classified modules" in item
        for item in result.investigation_summary
    )


def test_has_findings_when_service_reports_findings(agent, parsed_sources):
    result = agent.investigate(parsed_sources)

    assert result.has_findings


def test_completed_analyses_property(agent, parsed_sources):
    result = agent.investigate(parsed_sources)

    assert result.completed_analyses == (
        "architecture_patterns",
        "module_responsibilities",
        "code_flow",
        "execution_flow",
        "cross_module_relationships",
        "data_flow",
    )


def test_wraps_architecture_stage_exception(parsed_sources):
    architecture = FakeService(error=RuntimeError("architecture failed"))

    agent = AdvancedCodeInvestigationAgent(
        architecture_service=architecture,
        responsibility_service=FakeService(),
        code_flow_service=FakeService(),
        execution_flow_service=FakeService(),
        cross_module_service=FakeService(),
        data_flow_service=FakeService(),
    )

    with pytest.raises(AdvancedCodeInvestigationError) as exc:
        agent.investigate(parsed_sources)

    assert exc.value.stage == "architecture_pattern_detection"
    assert "architecture failed" in str(exc.value)


def test_wraps_execution_stage_exception(parsed_sources):
    execution = FakeService(error=RuntimeError("execution failed"))

    agent = AdvancedCodeInvestigationAgent(
        architecture_service=FakeService(),
        responsibility_service=FakeService(),
        code_flow_service=FakeService(),
        execution_flow_service=execution,
        cross_module_service=FakeService(),
        data_flow_service=FakeService(),
    )

    with pytest.raises(AdvancedCodeInvestigationError) as exc:
        agent.investigate(parsed_sources)

    assert exc.value.stage == "function_method_execution_paths"


def test_rejects_empty_parsed_sources():
    agent = AdvancedCodeInvestigationAgent()

    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate({})


@pytest.mark.parametrize(
    "value",
    [
        None,
        "main.py",
        ("main.py",),
        {"main.py"},
    ],
)
def test_rejects_invalid_parsed_sources(value):
    agent = AdvancedCodeInvestigationAgent()

    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate(value)


def test_rejects_parsed_source_without_language():
    agent = AdvancedCodeInvestigationAgent()

    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate({
            "main.py": SimpleNamespace(filename="main.py")
        })


def test_rejects_parsed_source_without_filename():
    agent = AdvancedCodeInvestigationAgent()

    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate({
            "main.py": SimpleNamespace(language="python")
        })


def test_rejects_parsed_source_filename_mismatch():
    agent = AdvancedCodeInvestigationAgent()

    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate({
            "main.py": SimpleNamespace(
                filename="other.py",
                language="python",
            )
        })


@pytest.mark.parametrize(
    "source_files",
    [
        "main.py",
        b"main.py",
        {"main.py"},
        ("",),
        ("main.py", "main.py"),
        ("other.py",),
    ],
)
def test_rejects_invalid_source_files(
    agent,
    parsed_sources,
    source_files,
):
    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate(
            parsed_sources,
            source_files=source_files,
        )


@pytest.mark.parametrize(
    "field",
    [
        "code_entities",
        "dependencies",
        "call_graphs",
    ],
)
def test_rejects_invalid_analysis_collections(
    agent,
    parsed_sources,
    field,
):
    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate(
            parsed_sources,
            **{field: "invalid"},
        )


@pytest.mark.parametrize(
    "entry_points",
    [
        "main.main",
        {"main.main"},
        {"entry": "main.main"},
        ("",),
        ("main.main", "main.main"),
    ],
)
def test_rejects_invalid_entry_points(
    agent,
    parsed_sources,
    entry_points,
):
    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate(
            parsed_sources,
            entry_points=entry_points,
        )


@pytest.mark.parametrize(
    "max_depth",
    [
        0,
        -1,
        True,
        1.5,
        "10",
    ],
)
def test_rejects_invalid_max_depth(agent, parsed_sources, max_depth):
    with pytest.raises(AdvancedCodeInvestigationError):
        agent.investigate(
            parsed_sources,
            max_depth=max_depth,
        )


def test_result_rejects_negative_file_count():
    with pytest.raises(AdvancedCodeInvestigationError):
        AdvancedCodeInvestigationResult(
            total_files=-1,
            analyzed_files=0,
            skipped_files=0,
            architecture_patterns=None,
            module_responsibilities=None,
            code_flow=None,
            execution_flow=None,
            cross_module_relationships=None,
            data_flow=None,
            investigation_summary=(),
        )


def test_result_rejects_inconsistent_file_counts():
    with pytest.raises(AdvancedCodeInvestigationError):
        AdvancedCodeInvestigationResult(
            total_files=1,
            analyzed_files=1,
            skipped_files=1,
            architecture_patterns=None,
            module_responsibilities=None,
            code_flow=None,
            execution_flow=None,
            cross_module_relationships=None,
            data_flow=None,
            investigation_summary=(),
        )


def test_result_rejects_invalid_summary():
    with pytest.raises(AdvancedCodeInvestigationError):
        AdvancedCodeInvestigationResult(
            total_files=0,
            analyzed_files=0,
            skipped_files=0,
            architecture_patterns=None,
            module_responsibilities=None,
            code_flow=None,
            execution_flow=None,
            cross_module_relationships=None,
            data_flow=None,
            investigation_summary=("valid", ""),
        )


def test_result_healthy_when_no_files_skipped():
    result = AdvancedCodeInvestigationResult(
        total_files=2,
        analyzed_files=2,
        skipped_files=0,
        architecture_patterns=None,
        module_responsibilities=None,
        code_flow=None,
        execution_flow=None,
        cross_module_relationships=None,
        data_flow=None,
        investigation_summary=(),
    )

    assert result.healthy


def test_result_not_healthy_when_files_skipped():
    result = AdvancedCodeInvestigationResult(
        total_files=2,
        analyzed_files=1,
        skipped_files=1,
        architecture_patterns=None,
        module_responsibilities=None,
        code_flow=None,
        execution_flow=None,
        cross_module_relationships=None,
        data_flow=None,
        investigation_summary=(),
    )

    assert not result.healthy


def test_investigation_is_deterministic(agent, parsed_sources):
    first = agent.investigate(parsed_sources)
    second = agent.investigate(parsed_sources)

    assert first.investigation_summary == second.investigation_summary
    assert first.total_files == second.total_files
