
import ast

import pytest

from app.application.language_parser import ParsedSource
from app.application.data_flow_analysis_service import (
    DataFlowAnalysisError,
    DataFlowAnalysisResult,
    DataFlowAnalysisService,
    DataFlowEdge,
    DataFlowNode,
    DataFlowPath,
)


@pytest.fixture
def service():
    return DataFlowAnalysisService()


def make_source(source, filename="sample.py", language="python"):
    tree = ast.parse(source)
    return ParsedSource(
        language=language,
        filename=filename,
        tree=tree,
        line_count=len(source.splitlines()),
    )


def test_analyze_simple_assignment_flow(service):
    source = make_source(
        """
def calculate():
    amount = 100
    total = amount
    return total
"""
    )

    result = service.analyze((source,))[0]

    assert result.analyzed
    assert result.has_data_flow
    assert result.total_nodes >= 3
    assert result.total_edges >= 2


def test_analyze_tracks_function_parameters(service):
    source = make_source(
        """
def calculate(amount):
    total = amount
    return total
"""
    )

    result = service.analyze((source,))[0]

    assert len(result.parameter_nodes) == 1
    assert result.parameter_nodes[0].name == "amount"
    assert any(
        edge.relationship_type == "assignment"
        for edge in result.edges
    )


def test_analyze_tracks_return_values(service):
    source = make_source(
        """
def calculate(amount):
    total = amount
    return total
"""
    )

    result = service.analyze((source,))[0]

    assert len(result.return_nodes) == 1
    assert result.return_nodes[0].expression == "total"
    assert any(
        edge.relationship_type == "return"
        for edge in result.edges
    )


def test_analyze_tracks_chained_assignments(service):
    source = make_source(
        """
def process(value):
    first = value
    second = first
    third = second
    return third
"""
    )

    result = service.analyze((source,))[0]

    assignment_edges = [
        edge for edge in result.edges
        if edge.relationship_type == "assignment"
    ]

    assert len(assignment_edges) >= 3


def test_analyze_tracks_variable_reassignment(service):
    source = make_source(
        """
def process(value):
    result = value
    result = result + 1
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        edge.relationship_type == "reassignment"
        for edge in result.edges
    )


def test_analyze_tracks_annotated_assignment(service):
    source = make_source(
        """
def process(value):
    result: int = value
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        node.operation == "annotated_assignment"
        for node in result.nodes
    )


def test_analyze_tracks_augmented_assignment(service):
    source = make_source(
        """
def process(value):
    result = value
    result += 5
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        edge.relationship_type == "reassignment"
        for edge in result.edges
    )


def test_analyze_tracks_call_arguments(service):
    source = make_source(
        """
def process(value):
    result = transform(value)
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert len(result.call_nodes) == 1
    assert any(
        edge.relationship_type == "argument"
        for edge in result.edges
    )


def test_analyze_tracks_keyword_call_arguments(service):
    source = make_source(
        """
def process(value):
    result = transform(data=value)
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        edge.relationship_type == "argument"
        for edge in result.edges
    )


def test_analyze_tracks_multiple_call_arguments(service):
    source = make_source(
        """
def process(first, second):
    result = combine(first, second)
    return result
"""
    )

    result = service.analyze((source,))[0]

    argument_edges = [
        edge for edge in result.edges
        if edge.relationship_type == "argument"
    ]

    assert len(argument_edges) == 2


def test_analyze_tracks_multiple_parameters(service):
    source = make_source(
        """
def process(first, second, third):
    return first
"""
    )

    result = service.analyze((source,))[0]

    assert len(result.parameter_nodes) == 3


def test_analyze_tracks_positional_only_and_keyword_only_parameters(
    service,
):
    source = make_source(
        """
def process(first, /, second, *, third):
    return first
"""
    )

    result = service.analyze((source,))[0]

    parameter_names = {
        node.name for node in result.parameter_nodes
    }

    assert parameter_names == {"first", "second", "third"}


def test_analyze_tracks_varargs_and_kwargs(service):
    source = make_source(
        """
def process(*args, **kwargs):
    return args
"""
    )

    result = service.analyze((source,))[0]

    parameter_names = {
        node.name for node in result.parameter_nodes
    }

    assert parameter_names == {"args", "kwargs"}


def test_analyze_tracks_nested_function_scope(service):
    source = make_source(
        """
def outer(value):
    def inner(data):
        result = data
        return result

    return value
"""
    )

    result = service.analyze((source,))[0]

    scopes = {node.scope for node in result.nodes}

    assert "<module>.outer" in scopes
    assert "<module>.outer.inner" in scopes


def test_analyze_tracks_class_method_scope(service):
    source = make_source(
        """
class Processor:
    def process(self, value):
        result = value
        return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        node.scope == "<module>.Processor.process"
        and node.operation == "parameter"
        for node in result.nodes
    )


def test_analyze_tracks_async_function(service):
    source = make_source(
        """
async def process(value):
    result = value
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert result.analyzed
    assert len(result.parameter_nodes) == 1
    assert len(result.return_nodes) == 1


def test_analyze_tracks_module_level_assignments(service):
    source = make_source(
        """
original = 10
copied = original
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        node.scope == "<module>"
        and node.name == "copied"
        for node in result.assignment_nodes
    )


def test_analyze_tracks_tuple_assignment(service):
    source = make_source(
        """
def process():
    first, second = (10, 20)
    return first
"""
    )

    result = service.analyze((source,))[0]

    assignment_names = {
        node.name for node in result.assignment_nodes
    }

    assert {"first", "second"}.issubset(assignment_names)


def test_analyze_tracks_for_loop_variable(service):
    source = make_source(
        """
def process(items):
    for item in items:
        result = item
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        node.name == "item"
        and node.operation == "assignment"
        for node in result.nodes
    )

    assert any(
        edge.relationship_type == "iteration"
        for edge in result.edges
    )


def test_analyze_tracks_with_statement_variable(service):
    source = make_source(
        """
def process(path):
    with open(path) as handle:
        result = handle
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        node.name == "handle"
        for node in result.nodes
    )

    assert any(
        edge.relationship_type == "context"
        for edge in result.edges
    )


def test_analyze_tracks_expression_origins(service):
    source = make_source(
        """
def process():
    first = 10
    second = "hello"
"""
    )

    result = service.analyze((source,))[0]

    origins = {
        node.origin_type for node in result.assignment_nodes
    }

    assert "expression" in origins


def test_analyze_tracks_expression_dependencies(service):
    source = make_source(
        """
def process(value):
    result = value + 10
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert any(
        edge.relationship_type == "assignment"
        for edge in result.edges
    )


def test_analyze_multiple_sources(service):
    first = make_source(
        "value = 10",
        filename="first.py",
    )
    second = make_source(
        "value = 20",
        filename="second.py",
    )

    results = service.analyze((first, second))

    assert len(results) == 2
    assert results[0].file_path == "first.py"
    assert results[1].file_path == "second.py"


def test_analyze_unsupported_language(service):
    source = make_source(
        "value = 10",
        filename="sample.js",
        language="javascript",
    )

    result = service.analyze((source,))[0]

    assert not result.analyzed
    assert result.syntax_error == "Unsupported language."
    assert result.total_nodes == 0
    assert result.total_edges == 0


def test_analyze_empty_python_module(service):
    source = make_source("")

    result = service.analyze((source,))[0]

    assert result.analyzed
    assert not result.has_data_flow
    assert result.total_nodes == 0
    assert result.total_edges == 0


def test_analyze_rejects_none_input(service):
    with pytest.raises(DataFlowAnalysisError):
        service.analyze(None)


@pytest.mark.parametrize(
    "invalid_input",
    [
        "source.py",
        b"source.py",
        {"source.py": "value = 1"},
        {"source.py"},
    ],
)
def test_analyze_rejects_invalid_source_collections(
    service,
    invalid_input,
):
    with pytest.raises(DataFlowAnalysisError):
        service.analyze(invalid_input)


def test_analyze_rejects_invalid_source_items(service):
    with pytest.raises(DataFlowAnalysisError):
        service.analyze((object(),))


def test_analyze_rejects_duplicate_filenames(service):
    first = make_source("value = 1", filename="sample.py")
    second = make_source("value = 2", filename="sample.py")

    with pytest.raises(
        DataFlowAnalysisError,
        match="filenames must be unique",
    ):
        service.analyze((first, second))


def test_data_flow_node_rejects_empty_identifier():
    with pytest.raises(DataFlowAnalysisError):
        DataFlowNode(
            node_id="",
            file_path="sample.py",
            scope="<module>",
            name="value",
            operation="assignment",
            line=1,
            expression="10",
            origin_type="expression",
        )


@pytest.mark.parametrize("line", [0, -1, True, "1"])
def test_data_flow_node_rejects_invalid_line(line):
    with pytest.raises(DataFlowAnalysisError):
        DataFlowNode(
            node_id="node-1",
            file_path="sample.py",
            scope="<module>",
            name="value",
            operation="assignment",
            line=line,
            expression="10",
            origin_type="expression",
        )


def test_data_flow_edge_rejects_empty_source():
    with pytest.raises(DataFlowAnalysisError):
        DataFlowEdge(
            source_node="",
            target_node="node-2",
            relationship_type="assignment",
            line=1,
        )


@pytest.mark.parametrize("line", [0, -1, True, "2"])
def test_data_flow_edge_rejects_invalid_line(line):
    with pytest.raises(DataFlowAnalysisError):
        DataFlowEdge(
            source_node="node-1",
            target_node="node-2",
            relationship_type="assignment",
            line=line,
        )


def test_data_flow_path_rejects_single_node():
    with pytest.raises(DataFlowAnalysisError):
        DataFlowPath(
            nodes=("node-1",),
            relationship_types=(),
        )


def test_data_flow_path_rejects_mismatched_relationship_count():
    with pytest.raises(DataFlowAnalysisError):
        DataFlowPath(
            nodes=("node-1", "node-2", "node-3"),
            relationship_types=("assignment",),
        )


def test_result_rejects_inconsistent_node_count():
    with pytest.raises(DataFlowAnalysisError):
        DataFlowAnalysisResult(
            file_path="sample.py",
            language="python",
            total_nodes=1,
            total_edges=0,
            total_paths=0,
            nodes=(),
            edges=(),
            paths=(),
            analyzed=True,
        )


def test_result_rejects_negative_counts():
    with pytest.raises(DataFlowAnalysisError):
        DataFlowAnalysisResult(
            file_path="sample.py",
            language="python",
            total_nodes=-1,
            total_edges=0,
            total_paths=0,
            nodes=(),
            edges=(),
            paths=(),
            analyzed=True,
        )


def test_result_exposes_source_and_destination_nodes(service):
    source = make_source(
        """
def process(value):
    result = value
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert result.source_nodes
    assert result.destination_nodes


def test_result_exposes_assignment_and_return_nodes(service):
    source = make_source(
        """
def process(value):
    result = value
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert result.assignment_nodes
    assert result.return_nodes


def test_paths_are_created_from_edges(service):
    source = make_source(
        """
def process(value):
    result = value
    return result
"""
    )

    result = service.analyze((source,))[0]

    assert result.total_paths == result.total_edges

    for path in result.paths:
        assert len(path.nodes) == 2
        assert len(path.relationship_types) == 1


def test_analysis_is_deterministic(service):
    source = make_source(
        """
def process(value):
    first = value
    second = first
    return second
"""
    )

    first_result = service.analyze((source,))[0]
    second_result = service.analyze((source,))[0]

    assert first_result.nodes == second_result.nodes
    assert first_result.edges == second_result.edges
    assert first_result.paths == second_result.paths

