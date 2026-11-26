
import ast

import pytest

from appy.application.advanced_code_flow_tracing_service import (
    AdvancedCodeFlowTracingError,
    AdvancedCodeFlowTracingService,
)
from appy.application.language_parser import ParsedSource


def parsed_source(source: str, filename: str = "sample.py"):
    return ParsedSource(
        language="python",
        filename=filename,
        tree=ast.parse(source),
        line_count=len(source.splitlines()),
    )


@pytest.fixture
def service():
    return AdvancedCodeFlowTracingService()


def test_analyze_empty_repository(service):
    result = service.analyze({})

    assert result.total_files == 0
    assert result.analyzed_files == 0
    assert result.total_entities == 0
    assert result.total_calls == 0
    assert result.nodes == ()
    assert result.edges == ()
    assert result.traces == ()


def test_analyze_single_file_with_function_calls(service):
    source = """
def main():
    helper()

def helper():
    return 10
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.total_files == 1
    assert result.analyzed_files == 1
    assert result.total_entities == 3
    assert result.total_calls == 1
    assert result.resolved_calls == 1
    assert result.unresolved_calls == 0
    assert len(result.edges) == 1
    assert result.edges[0].caller == "sample.main"
    assert result.edges[0].callee == "sample.helper"


def test_discovers_entry_points(service):
    source = """
def main():
    helper()

def helper():
    return 10

def unused():
    return 20
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.entry_points == (
        "sample.main",
        "sample.unused",
    )


def test_traces_function_execution_path(service):
    source = """
def main():
    first()

def first():
    second()

def second():
    return 10
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    trace = next(
        trace
        for trace in result.traces
        if trace.entry_point == "sample.main"
    )

    assert trace.path == (
        "sample.main",
        "sample.first",
        "sample.second",
    )
    assert trace.depth == 2
    assert trace.is_recursive is False
    assert trace.terminated_by_depth_limit is False


def test_traces_class_methods(service):
    source = """
class Worker:
    def run(self):
        self.process()

    def process(self):
        return 1
"""

    result = service.analyze(
        {"worker.py": parsed_source(source, "worker.py")}
    )

    assert any(
        edge.caller == "worker.Worker.run"
        and edge.callee == "worker.Worker.process"
        for edge in result.edges
    )


def test_records_unresolved_external_calls(service):
    source = """
def main():
    print("hello")
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.total_calls == 1
    assert result.resolved_calls == 0
    assert result.unresolved_calls == 1
    assert result.has_unresolved_calls


def test_supports_explicit_entry_points(service):
    source = """
def main():
    helper()

def helper():
    return 1
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)},
        entry_points=["sample.main"],
    )

    assert result.entry_points == ("sample.main",)
    assert all(
        trace.entry_point == "sample.main"
        for trace in result.traces
    )


def test_rejects_unknown_entry_point(service):
    source = """
def main():
    return 1
"""

    with pytest.raises(
        AdvancedCodeFlowTracingError,
        match="Unknown entry point",
    ):
        service.analyze(
            {"sample.py": parsed_source(source)},
            entry_points=["sample.missing"],
        )


def test_rejects_invalid_source_mapping(service):
    with pytest.raises(AdvancedCodeFlowTracingError):
        service.analyze([])


def test_rejects_invalid_parsed_source(service):
    with pytest.raises(AdvancedCodeFlowTracingError):
        service.analyze({"sample.py": "not parsed source"})


def test_rejects_filename_mismatch(service):
    source = parsed_source(
        "def main():\n    return 1",
        "other.py",
    )

    with pytest.raises(
        AdvancedCodeFlowTracingError,
        match="does not match",
    ):
        service.analyze({"sample.py": source})


@pytest.mark.parametrize(
    "max_depth",
    [0, -1, 1.5, True, "5"],
)
def test_rejects_invalid_max_depth(service, max_depth):
    with pytest.raises(AdvancedCodeFlowTracingError):
        service.analyze({}, max_depth=max_depth)


def test_rejects_invalid_entry_points(service):
    with pytest.raises(AdvancedCodeFlowTracingError):
        service.analyze(
            {},
            entry_points="sample.main",
        )


def test_rejects_empty_entry_point(service):
    with pytest.raises(AdvancedCodeFlowTracingError):
        service.analyze(
            {},
            entry_points=[""],
        )


def test_rejects_duplicate_entry_points(service):
    with pytest.raises(AdvancedCodeFlowTracingError):
        service.analyze(
            {},
            entry_points=[
                "sample.main",
                "sample.main",
            ],
        )


def test_skips_unsupported_languages(service):
    source = ParsedSource(
        language="javascript",
        filename="sample.js",
        tree=ast.parse("pass"),
        line_count=1,
    )

    result = service.analyze(
        {"sample.js": source}
    )

    assert result.total_files == 1
    assert result.analyzed_files == 0
    assert result.skipped_files == 1
    assert result.total_entities == 0


def test_respects_maximum_trace_depth(service):
    source = """
def main():
    first()

def first():
    second()

def second():
    third()

def third():
    return 1
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)},
        entry_points=["sample.main"],
        max_depth=1,
    )

    assert any(
        trace.terminated_by_depth_limit
        for trace in result.traces
    )

    assert result.maximum_trace_depth == 1


def test_detects_recursive_call(service):
    source = """
def first():
    second()

def second():
    first()
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)},
        entry_points=["sample.first"],
    )

    assert any(
        trace.is_recursive
        for trace in result.traces
    )

    recursive_trace = next(
        trace
        for trace in result.traces
        if trace.is_recursive
    )

    assert recursive_trace.path == (
        "sample.first",
        "sample.second",
        "sample.first",
    )


def test_handles_multiple_files(service):
    first = """
def main():
    helper()
"""

    second = """
def helper():
    return 1
"""

    result = service.analyze(
        {
            "first.py": parsed_source(first, "first.py"),
            "second.py": parsed_source(second, "second.py"),
        }
    )

    assert result.total_files == 2
    assert result.analyzed_files == 2
    assert result.total_entities == 4
    assert result.total_calls == 1
    assert result.unresolved_calls == 0


def test_result_properties(service):
    source = """
def main():
    helper()

def helper():
    return 1
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.has_traces is True
    assert result.has_unresolved_calls is False
    assert result.maximum_trace_depth == 1
    assert result.recursive_traces == ()


def test_trace_contains_source_line_information(service):
    source = """
def main():
    helper()

def helper():
    return 1
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    edge = result.edges[0]

    assert edge.filename == "sample.py"
    assert edge.line == 3
    assert edge.call_type == "function"


def test_nodes_are_deterministically_sorted(service):
    source = """
def zulu():
    return 1

def alpha():
    return 2
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.nodes == tuple(
        sorted(
            result.nodes,
            key=lambda node: (
                node.filename,
                node.line,
                node.qualified_name,
            ),
        )
    )


def test_result_contains_all_entity_types(service):
    source = """
class Worker:
    def run(self):
        return 1

def helper():
    return 2
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    entity_types = {
        node.entity_type for node in result.nodes
    }

    assert entity_types == {
        "module",
        "class",
        "method",
        "function",
    }


def test_handles_async_function_calls(service):
    source = """
async def main():
    await helper()

async def helper():
    return 1
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.total_calls == 1
    assert result.resolved_calls == 1
    assert result.edges[0].caller == "sample.main"
    assert result.edges[0].callee == "sample.helper"


def test_handles_nested_functions(service):
    source = """
def main():
    def inner():
        return 1

    inner()
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert any(
        edge.caller == "sample.main"
        and edge.callee == "sample.main.inner"
        for edge in result.edges
    )


def test_does_not_mutate_input_mapping(service):
    source = parsed_source(
        "def main():\n    return 1"
    )
    sources = {"sample.py": source}
    original = dict(sources)

    service.analyze(sources)

    assert sources == original


def test_empty_explicit_entry_points_produce_no_traces(service):
    source = """
def main():
    return 1
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)},
        entry_points=[],
    )

    assert result.entry_points == ()
    assert result.traces == ()


def test_handles_module_level_calls(service):
    source = """
def helper():
    return 1

helper()
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.total_calls == 1
    assert result.unresolved_calls == 1


def test_trace_depth_property_for_empty_result(service):
    result = service.analyze({})

    assert result.maximum_trace_depth == 0


def test_detects_multiple_independent_entry_points(service):
    source = """
def first():
    return 1

def second():
    return 2
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.entry_points == (
        "sample.first",
        "sample.second",
    )


def test_preserves_multiple_call_edges(service):
    source = """
def main():
    helper()
    helper()

def helper():
    return 1
"""

    result = service.analyze(
        {"sample.py": parsed_source(source)}
    )

    assert result.total_calls == 2
    assert result.resolved_calls == 2
    assert len(result.edges) == 2
