
"""Tests for CircularDependencyDetectionService."""

from dataclasses import FrozenInstanceError

import pytest

from app.application.circular_dependency_detection_service import (
    CircularDependency,
    CircularDependencyDetectionError,
    CircularDependencyDetectionResult,
    CircularDependencyDetectionService,
)
from app.application.dependency_analyzer import DependencyRecord


@pytest.fixture
def service():
    return CircularDependencyDetectionService()


def dependency(
    source,
    target,
    dependency_type="internal",
    line=1,
    imported_name=None,
    alias=None,
):
    return DependencyRecord(
        source_file=source,
        imported_module=target,
        imported_name=imported_name,
        alias=alias,
        dependency_type=dependency_type,
        line=line,
        is_relative=False,
    )


def test_empty_dependencies_return_empty_result(service):
    result = service.analyze([])

    assert result.total_dependencies == 0
    assert result.dependencies_checked == 0
    assert result.internal_dependencies == 0
    assert result.ignored_dependencies == 0
    assert result.total_modules == 0
    assert result.cycle_count == 0
    assert result.cycles == ()
    assert result.has_cycles is False
    assert result.healthy is True


def test_single_internal_dependency_has_no_cycle(service):
    result = service.analyze(
        [dependency("app/a.py", "app.b")],
        internal_modules=["app.a", "app.b"],
    )

    assert result.total_modules == 2
    assert result.internal_dependencies == 1
    assert result.cycle_count == 0
    assert result.healthy is True


def test_detects_two_module_cycle(service):
    result = service.analyze(
        [
            dependency("app/a.py", "app.b"),
            dependency("app/b.py", "app.a"),
        ],
        internal_modules=["app.a", "app.b"],
    )

    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("app.a", "app.b", "app.a")
    assert result.cycles[0].dependency_count == 2
    assert result.has_cycles is True
    assert result.healthy is False


def test_detects_three_module_cycle(service):
    result = service.analyze(
        [
            dependency("app/a.py", "app.b"),
            dependency("app/b.py", "app.c"),
            dependency("app/c.py", "app.a"),
        ],
        internal_modules=["app.a", "app.b", "app.c"],
    )

    assert result.cycle_count == 1
    assert result.cycles[0].modules == (
        "app.a",
        "app.b",
        "app.c",
        "app.a",
    )


def test_detects_self_dependency_cycle(service):
    result = service.analyze(
        [dependency("app/a.py", "app.a")],
        internal_modules=["app.a"],
    )

    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("app.a", "app.a")
    assert result.cycles[0].dependency_count == 1


def test_external_dependencies_are_ignored(service):
    result = service.analyze(
        [
            dependency("app/a.py", "app.b"),
            dependency("app/b.py", "requests", "external"),
            dependency("app/b.py", "app.a"),
        ],
        internal_modules=["app.a", "app.b"],
    )

    assert result.total_dependencies == 3
    assert result.internal_dependencies == 2
    assert result.ignored_dependencies == 1
    assert result.cycle_count == 1


def test_unresolved_dependencies_are_ignored(service):
    result = service.analyze(
        [
            dependency("app/a.py", "app.b"),
            dependency("app/b.py", "unknown", "unresolved"),
        ],
        internal_modules=["app.a", "app.b"],
    )

    assert result.internal_dependencies == 1
    assert result.ignored_dependencies == 1
    assert result.cycle_count == 0


def test_detects_multiple_independent_cycles(service):
    records = [
        dependency("a.py", "b"),
        dependency("b.py", "a"),
        dependency("c.py", "d"),
        dependency("d.py", "c"),
    ]

    result = service.analyze(records, internal_modules=["a", "b", "c", "d"])

    assert result.cycle_count == 2
    assert [cycle.modules for cycle in result.cycles] == [
        ("a", "b", "a"),
        ("c", "d", "c"),
    ]


def test_detects_overlapping_cycles(service):
    records = [
        dependency("a.py", "b"),
        dependency("b.py", "a"),
        dependency("b.py", "c"),
        dependency("c.py", "b"),
    ]

    result = service.analyze(records, internal_modules=["a", "b", "c"])

    assert result.cycle_count == 2
    assert [cycle.modules for cycle in result.cycles] == [
        ("a", "b", "a"),
        ("b", "c", "b"),
    ]


def test_detects_distinct_cycles_in_three_node_graph(service):
    records = [
        dependency("a.py", "b"),
        dependency("b.py", "c"),
        dependency("c.py", "a"),
        dependency("a.py", "c"),
        dependency("c.py", "b"),
    ]

    result = service.analyze(records, internal_modules=["a", "b", "c"])

    cycles = {cycle.modules for cycle in result.cycles}
    assert ("a", "b", "c", "a") in cycles
    assert ("a", "c", "a") in cycles
    assert ("b", "c", "b") in cycles


def test_duplicate_dependency_records_do_not_duplicate_cycles(service):
    records = [
        dependency("a.py", "b", line=1),
        dependency("a.py", "b", line=2),
        dependency("b.py", "a"),
    ]

    result = service.analyze(records, internal_modules=["a", "b"])

    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("a", "b", "a")


def test_module_paths_are_normalized(service):
    result = service.analyze(
        [
            dependency("app\\a.py", "app.b"),
            dependency("app\\b.py", "app.a"),
        ],
        internal_modules=["app/a.py", "app/b.py"],
    )

    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("app.a", "app.b", "app.a")


def test_init_files_are_normalized_to_package_modules(service):
    result = service.analyze(
        [
            dependency("app/a.py", "app.b"),
            dependency("app/b/__init__.py", "app.a"),
        ],
        internal_modules=["app.a", "app.b"],
    )

    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("app.a", "app.b", "app.a")


def test_module_to_file_mapping_resolves_nonstandard_paths(service):
    result = service.analyze(
        [
            dependency("src/first_module.py", "second"),
            dependency("src/second_module.py", "first"),
        ],
        internal_modules=["first", "second"],
        module_to_file={
            "first": "src/first_module.py",
            "second": "src/second_module.py",
        },
    )

    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("first", "second", "first")


def test_module_to_file_mapping_supports_windows_paths(service):
    result = service.analyze(
        [
            dependency("src\\first.py", "second"),
            dependency("src\\second.py", "first"),
        ],
        internal_modules=["first", "second"],
        module_to_file={
            "first": "src\\first.py",
            "second": "src\\second.py",
        },
    )

    assert result.cycle_count == 1


def test_modules_are_inferred_when_inventory_is_omitted(service):
    result = service.analyze(
        [
            dependency("pkg/a.py", "pkg.b"),
            dependency("pkg/b.py", "pkg.a"),
        ]
    )

    assert result.total_modules == 2
    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("pkg.a", "pkg.b", "pkg.a")


def test_unmapped_internal_dependency_does_not_create_false_cycle(service):
    result = service.analyze(
        [
            dependency("unknown/source.py", "app.b"),
            dependency("app/b.py", "unknown.source"),
        ],
        internal_modules=["app.b"],
    )

    assert result.cycle_count == 0
    assert result.internal_dependencies == 2


def test_modules_in_cycles_returns_sorted_unique_modules(service):
    result = service.analyze(
        [
            dependency("z.py", "a"),
            dependency("a.py", "z"),
            dependency("b.py", "c"),
            dependency("c.py", "b"),
        ],
        internal_modules=["a", "b", "c", "z"],
    )

    assert result.modules_in_cycles == ("a", "b", "c", "z")


def test_cycle_ids_are_deterministic(service):
    records = [
        dependency("a.py", "b"),
        dependency("b.py", "a"),
    ]

    first = service.analyze(records, internal_modules=["a", "b"])
    second = service.analyze(records, internal_modules=["b", "a"])

    assert first.cycles[0].cycle_id == second.cycles[0].cycle_id


def test_cycle_results_are_deterministically_sorted(service):
    records = [
        dependency("z.py", "y"),
        dependency("y.py", "z"),
        dependency("b.py", "a"),
        dependency("a.py", "b"),
    ]

    first = service.analyze(records, internal_modules=["z", "y", "b", "a"])
    second = service.analyze(records, internal_modules=["a", "b", "y", "z"])

    assert first.cycles == second.cycles


def test_input_records_are_not_modified(service):
    records = [
        dependency("a.py", "b"),
        dependency("b.py", "a"),
    ]
    original = tuple(records)

    service.analyze(records, internal_modules=["a", "b"])

    assert tuple(records) == original


def test_generator_dependencies_are_supported(service):
    records = (
        dependency(source, target)
        for source, target in [("a.py", "b"), ("b.py", "a")]
    )

    result = service.analyze(records, internal_modules=["a", "b"])

    assert result.cycle_count == 1
    assert result.total_dependencies == 2


def test_generator_internal_modules_are_supported(service):
    modules = (module for module in ["a", "b"])
    result = service.analyze(
        [dependency("a.py", "b"), dependency("b.py", "a")],
        internal_modules=modules,
    )

    assert result.cycle_count == 1


@pytest.mark.parametrize(
    "invalid_dependencies",
    [
        None,
        "not-a-dependency-list",
        b"bytes",
        {"invalid"},
        frozenset(),
        {"key": "value"},
        [object()],
    ],
)
def test_invalid_dependencies_raise_error(service, invalid_dependencies):
    with pytest.raises(CircularDependencyDetectionError):
        service.analyze(invalid_dependencies)


@pytest.mark.parametrize(
    "invalid_modules",
    [
        "app.module",
        b"app.module",
        {"app.module"},
        frozenset({"app.module"}),
        {"module": "path"},
        [""],
        [None],
        [1],
        ["."],
        ["app..module"],
    ],
)
def test_invalid_internal_modules_raise_error(service, invalid_modules):
    with pytest.raises(CircularDependencyDetectionError):
        service.analyze([], internal_modules=invalid_modules)


@pytest.mark.parametrize(
    "invalid_mapping",
    [
        [],
        "not-a-mapping",
        {"": "file.py"},
        {"module": ""},
        {"module": None},
        {None: "file.py"},
        {"bad module": "file.py"},
    ],
)
def test_invalid_module_to_file_mapping_raises_error(service, invalid_mapping):
    with pytest.raises(CircularDependencyDetectionError):
        service.analyze([], module_to_file=invalid_mapping)


def test_duplicate_normalized_internal_modules_raise_error(service):
    with pytest.raises(CircularDependencyDetectionError):
        service.analyze(
            [],
            internal_modules=["app/module.py", "app.module"],
        )


def test_duplicate_normalized_mapping_keys_raise_error(service):
    class DuplicateKeyMapping(dict):
        def items(self):
            return [
                ("app/module.py", "one.py"),
                ("app.module", "two.py"),
            ]

    with pytest.raises(CircularDependencyDetectionError):
        service.analyze([], module_to_file=DuplicateKeyMapping())


def test_circular_dependency_model_is_immutable():
    cycle = CircularDependency(
        cycle_id="abc123",
        modules=("a", "b", "a"),
        dependency_count=2,
    )

    with pytest.raises(FrozenInstanceError):
        cycle.cycle_id = "changed"


def test_invalid_circular_dependency_model_rejects_open_chain():
    with pytest.raises(CircularDependencyDetectionError):
        CircularDependency(
            cycle_id="abc",
            modules=("a", "b"),
            dependency_count=1,
        )


def test_invalid_circular_dependency_model_rejects_repeated_intermediate():
    with pytest.raises(CircularDependencyDetectionError):
        CircularDependency(
            cycle_id="abc",
            modules=("a", "b", "c", "b", "a"),
            dependency_count=4,
        )


def test_invalid_circular_dependency_model_rejects_wrong_edge_count():
    with pytest.raises(CircularDependencyDetectionError):
        CircularDependency(
            cycle_id="abc",
            modules=("a", "b", "a"),
            dependency_count=1,
        )


def test_result_model_rejects_inconsistent_counts():
    with pytest.raises(CircularDependencyDetectionError):
        CircularDependencyDetectionResult(
            total_dependencies=2,
            dependencies_checked=2,
            internal_dependencies=2,
            ignored_dependencies=1,
            total_modules=2,
            cycle_count=0,
            cycles=(),
        )


def test_result_model_rejects_incorrect_cycle_count():
    with pytest.raises(CircularDependencyDetectionError):
        CircularDependencyDetectionResult(
            total_dependencies=0,
            dependencies_checked=0,
            internal_dependencies=0,
            ignored_dependencies=0,
            total_modules=0,
            cycle_count=1,
            cycles=(),
        )


def test_dependency_line_and_import_metadata_do_not_change_graph(service):
    result = service.analyze(
        [
            dependency("a.py", "b", line=12, imported_name="Thing", alias="T"),
            dependency("b.py", "a", line=20, imported_name="Other"),
        ],
        internal_modules=["a", "b"],
    )

    assert result.cycle_count == 1
    assert result.cycles[0].modules == ("a", "b", "a")


def test_multiple_edges_between_same_modules_are_one_graph_edge(service):
    result = service.analyze(
        [
            dependency("a.py", "b", line=1),
            dependency("a.py", "b", line=2),
            dependency("b.py", "a", line=3),
        ],
        internal_modules=["a", "b"],
    )

    assert result.cycle_count == 1
    assert result.cycles[0].dependency_count == 2


def test_acyclic_chain_with_branch_is_healthy(service):
    result = service.analyze(
        [
            dependency("a.py", "b"),
            dependency("a.py", "c"),
            dependency("b.py", "d"),
            dependency("c.py", "d"),
        ],
        internal_modules=["a", "b", "c", "d"],
    )

    assert result.cycle_count == 0
    assert result.has_cycles is False
    assert result.healthy is True


def test_cycle_detection_uses_dependency_direction(service):
    result = service.analyze(
        [
            dependency("a.py", "b"),
            dependency("c.py", "b"),
            dependency("c.py", "a"),
        ],
        internal_modules=["a", "b", "c"],
    )

    assert result.cycle_count == 0
