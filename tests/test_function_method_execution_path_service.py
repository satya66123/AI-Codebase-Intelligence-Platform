
import ast

import pytest

from appy.application.function_method_execution_path_service import (
    ExecutionPathStatus,
    FunctionMethodExecutionPathError,
    FunctionMethodExecutionPathService,
)
from appy.application.language_parser import ParsedSource


@pytest.fixture
def service():
    return FunctionMethodExecutionPathService()


def parsed_source(filename, source, language="python"):
    tree = (
        ast.parse(source)
        if language.lower() == "python"
        else ast.parse("pass")
    )

    return ParsedSource(
        language=language,
        filename=filename,
        tree=tree,
        line_count=len(source.splitlines()),
    )


def test_empty_sources_returns_empty_result(service):
    result = service.analyze({})

    assert result.total_files == 0
    assert result.analyzed_files == 0
    assert result.total_entities == 0
    assert result.total_calls == 0
    assert result.execution_paths == ()
    assert result.healthy is True


def test_analyzes_single_python_file(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def first():
    second()

def second():
    pass
""",
            )
        }
    )

    assert result.total_files == 1
    assert result.analyzed_files == 1
    assert result.skipped_files == 0
    assert result.total_functions == 2
    assert result.total_methods == 0


def test_traces_simple_function_execution_path(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    first()

def first():
    second()

def second():
    pass
""",
            )
        },
        entry_points=["main.main"],
    )

    assert result.total_execution_paths == 1

    path = result.execution_paths[0]

    assert path.path == (
        "main.main",
        "main.first",
        "main.second",
    )
    assert path.depth == 2
    assert path.is_recursive is False


def test_traces_method_execution_path(service):
    result = service.analyze(
        {
            "worker.py": parsed_source(
                "worker.py",
                """
class Worker:
    def run(self):
        self.process()

    def process(self):
        self.finish()

    def finish(self):
        pass
""",
            )
        },
        entry_points=["worker.Worker.run"],
    )

    assert result.total_execution_paths == 1

    path = result.execution_paths[0]

    assert path.path == (
        "worker.Worker.run",
        "worker.Worker.process",
        "worker.Worker.finish",
    )
    assert path.depth == 2


def test_detects_recursive_function_call(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def recursive():
    recursive()
""",
            )
        },
        entry_points=["main.recursive"],
    )

    assert result.has_recursive_paths is True

    path = result.execution_paths[0]

    assert path.is_recursive is True
    assert path.path == (
        "main.recursive",
        "main.recursive",
    )


def test_detects_mutually_recursive_functions(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def first():
    second()

def second():
    first()
""",
            )
        },
        entry_points=["main.first"],
    )

    assert result.has_recursive_paths is True

    path = result.execution_paths[0]

    assert path.is_recursive is True
    assert path.path == (
        "main.first",
        "main.second",
        "main.first",
    )


def test_respects_maximum_execution_depth(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def first():
    second()

def second():
    third()

def third():
    fourth()

def fourth():
    pass
""",
            )
        },
        entry_points=["main.first"],
        max_depth=2,
    )

    path = result.execution_paths[0]

    assert path.depth == 2
    assert path.terminated_by_depth_limit is True
    assert len(path.steps) == 2


def test_supports_cross_module_function_calls(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    helper()
""",
            ),
            "helper.py": parsed_source(
                "helper.py",
                """
def helper():
    finish()

def finish():
    pass
""",
            ),
        },
        entry_points=["main.main"],
    )

    path = result.execution_paths[0]

    assert path.path == (
        "main.main",
        "helper.helper",
        "helper.finish",
    )
    assert path.depth == 2


def test_supports_multiple_execution_branches(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    first()
    second()

def first():
    pass

def second():
    pass
""",
            )
        },
        entry_points=["main.main"],
    )

    assert result.total_execution_paths == 2

    paths = {
        path.path
        for path in result.execution_paths
    }

    assert (
        "main.main",
        "main.first",
    ) in paths

    assert (
        "main.main",
        "main.second",
    ) in paths


def test_supports_nested_function_calls(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def outer():
    def inner():
        finish()

    inner()

def finish():
    pass
""",
            )
        },
        entry_points=["main.outer"],
    )

    path = result.execution_paths[0]

    assert path.path == (
        "main.outer",
        "main.outer.inner",
        "main.finish",
    )


def test_resolves_async_function_calls(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
async def main():
    await helper()

async def helper():
    pass
""",
            )
        },
        entry_points=["main.main"],
    )

    path = result.execution_paths[0]

    assert path.path == (
        "main.main",
        "main.helper",
    )


def test_tracks_execution_steps(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    helper()

def helper():
    pass
""",
            )
        },
        entry_points=["main.main"],
    )

    assert len(result.execution_steps) == 1

    step = result.execution_steps[0]

    assert step.caller == "main.main"
    assert step.callee == "helper"
    assert step.target == "main.helper"
    assert step.status == ExecutionPathStatus.RESOLVED


def test_tracks_unresolved_calls(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    unknown_function()
""",
            )
        },
        entry_points=["main.main"],
    )

    assert result.unresolved_calls == 1
    assert result.has_unresolved_calls is True
    assert result.healthy is False


def test_tracks_builtin_calls_as_unresolved_references(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    print("hello")
""",
            )
        },
        entry_points=["main.main"],
    )

    assert result.unresolved_calls == 1
    assert result.unresolved_references[0].callee == "print"


def test_ignores_module_level_calls_for_function_paths(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def helper():
    pass

helper()
""",
            )
        }
    )

    assert result.total_calls == 1
    assert result.total_execution_paths == 1
    assert result.execution_paths[0].entry_point == "main.helper"
    assert result.execution_paths[0].depth == 0


def test_discovers_root_functions_automatically(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    helper()

def helper():
    pass

def independent():
    pass
""",
            )
        }
    )

    entry_points = {
        path.entry_point
        for path in result.execution_paths
    }

    assert entry_points == {
        "main.main",
        "main.independent",
    }


def test_accepts_simple_entry_point_name_when_unique(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    helper()

def helper():
    pass
""",
            )
        },
        entry_points=["main"],
    )

    assert result.total_entry_points == 1
    assert result.execution_paths[0].entry_point == "main.main"


def test_rejects_unknown_entry_point(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="was not found",
    ):
        service.analyze(
            {
                "main.py": parsed_source(
                    "main.py",
                    "def main(): pass",
                )
            },
            entry_points=["missing"],
        )


def test_rejects_ambiguous_simple_entry_point(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="ambiguous",
    ):
        service.analyze(
            {
                "first.py": parsed_source(
                    "first.py",
                    "def run(): pass",
                ),
                "second.py": parsed_source(
                    "second.py",
                    "def run(): pass",
                ),
            },
            entry_points=["run"],
        )


def test_rejects_invalid_max_depth(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="greater than zero",
    ):
        service.analyze({}, max_depth=0)


def test_rejects_boolean_max_depth(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="integer",
    ):
        service.analyze({}, max_depth=True)


def test_rejects_non_integer_max_depth(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="integer",
    ):
        service.analyze({}, max_depth=1.5)


def test_rejects_string_entry_points(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="not a single string",
    ):
        service.analyze(
            {},
            entry_points="main",
        )


def test_rejects_invalid_entry_point_collection(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="list or tuple",
    ):
        service.analyze(
            {},
            entry_points={"main"},
        )


def test_rejects_empty_entry_point_name(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="non-empty",
    ):
        service.analyze(
            {},
            entry_points=[""],
        )


def test_rejects_duplicate_entry_points(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="duplicate",
    ):
        service.analyze(
            {},
            entry_points=["main", "main"],
        )


def test_rejects_non_mapping_sources(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="mapping",
    ):
        service.analyze([])


def test_rejects_invalid_parsed_source(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="Invalid ParsedSource",
    ):
        service.analyze(
            {"main.py": "invalid"},
        )


def test_rejects_mismatched_source_filename(service):
    with pytest.raises(
        FunctionMethodExecutionPathError,
        match="does not match",
    ):
        service.analyze(
            {
                "main.py": parsed_source(
                    "different.py",
                    "pass",
                )
            }
        )


@pytest.mark.parametrize(
    "invalid_path",
    [
        "",
        "/absolute/main.py",
        "../main.py",
        "appy/../main.py",
        "appy//main.py",
        "./main.py",
    ],
)
def test_rejects_invalid_source_paths(service, invalid_path):
    with pytest.raises(FunctionMethodExecutionPathError):
        service.analyze(
            {
                invalid_path: parsed_source(
                    invalid_path,
                    "pass",
                )
            }
        )


def test_skips_non_python_sources(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                "def main(): pass",
            ),
            "frontend.js": parsed_source(
                "frontend.js",
                "function main() {}",
                language="javascript",
            ),
        }
    )

    assert result.total_files == 2
    assert result.analyzed_files == 1
    assert result.skipped_files == 1


def test_skips_all_non_python_sources(service):
    result = service.analyze(
        {
            "frontend.js": parsed_source(
                "frontend.js",
                "function main() {}",
                language="javascript",
            )
        }
    )

    assert result.analyzed_files == 0
    assert result.skipped_files == 1
    assert result.total_functions == 0


@pytest.mark.parametrize(
    ("source_path", "expected_module"),
    [
        ("main.py", "main"),
        ("folder/main.py", "folder.main"),
        ("appy/__init__.py", "appy"),
        ("appy/application/__init__.py", "appy.application"),
        ("appy/application/service.py", "appy.application.service"),
    ],
)
def test_gets_fully_qualified_module_name(source_path, expected_module):
    assert (
        FunctionMethodExecutionPathService._get_module_name(source_path)
        == expected_module
    )


def test_allows_same_filename_in_different_packages(service):
    result = service.analyze(
        {
            "main.py": parsed_source("main.py", "pass"),
            "folder/main.py": parsed_source(
                "folder/main.py",
                "pass",
            ),
        }
    )

    assert result.total_files == 2
    assert result.analyzed_files == 2


def test_allows_nested_package_initializer_files(service):
    result = service.analyze(
        {
            "appy/__init__.py": parsed_source(
                "appy/__init__.py",
                "pass",
            ),
            "appy/application/__init__.py": parsed_source(
                "appy/application/__init__.py",
                "pass",
            ),
        }
    )

    assert result.total_files == 2
    assert result.analyzed_files == 2

def test_supports_module_file_and_matching_package_initializer(service):
    sources = {
        "appy.py": parsed_source(
            "appy.py",
            "pass",
        ),
        "appy/__init__.py": parsed_source(
            "appy/__init__.py",
            "pass",
        ),
    }

    result = service.analyze(sources)

    assert result.total_files == 2
    assert result.analyzed_files == 2


def test_counts_functions_and_methods(service):
    result = service.analyze(
        {
            "worker.py": parsed_source(
                "worker.py",
                """
def standalone():
    pass

class Worker:
    def run(self):
        pass

    def stop(self):
        pass
""",
            )
        }
    )

    assert result.total_functions == 1
    assert result.total_methods == 2


def test_reports_maximum_execution_depth(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def first():
    second()

def second():
    third()

def third():
    pass
""",
            )
        },
        entry_points=["main.first"],
    )

    assert result.maximum_execution_depth == 2


def test_results_are_deterministic(service):
    first = {
        "main.py": parsed_source(
            "main.py",
            """
def main():
    beta()
    alpha()

def alpha():
    pass

def beta():
    pass
""",
        )
    }

    second = {
        "main.py": first["main.py"],
    }

    result_one = service.analyze(first)
    result_two = service.analyze(second)

    assert result_one.execution_paths == result_two.execution_paths
    assert result_one.execution_steps == result_two.execution_steps


def test_supports_method_to_method_recursion(service):
    result = service.analyze(
        {
            "worker.py": parsed_source(
                "worker.py",
                """
class Worker:
    def run(self):
        self.process()

    def process(self):
        self.run()
""",
            )
        },
        entry_points=["worker.Worker.run"],
    )

    assert result.has_recursive_paths is True
    assert result.execution_paths[0].is_recursive is True


def test_supports_multiple_entry_points(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def first():
    helper()

def second():
    helper()

def helper():
    pass
""",
            )
        },
        entry_points=["main.first", "main.second"],
    )

    assert result.total_entry_points == 2
    assert result.total_execution_paths == 2


def test_unresolved_call_does_not_create_execution_edge(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def main():
    missing_function()
""",
            )
        },
        entry_points=["main.main"],
    )

    path = result.execution_paths[0]

    assert path.path == ("main.main",)
    assert path.steps == ()
    assert result.unresolved_calls == 1


def test_depth_limited_paths_property(service):
    result = service.analyze(
        {
            "main.py": parsed_source(
                "main.py",
                """
def first():
    second()

def second():
    third()

def third():
    pass
""",
            )
        },
        entry_points=["main.first"],
        max_depth=1,
    )

    assert len(result.depth_limited_paths) == 1
    assert result.depth_limited_paths[0].terminated_by_depth_limit

def test_supports_module_file_and_matching_package_initializer(service):
    sources = {
        "appy.py": parsed_source(
            "appy.py",
            """
def main():
    return True
""",
        ),
        "appy/__init__.py": parsed_source(
            "appy/__init__.py",
            """
def initialize():
    return True
""",
        ),
    }

    result = service.analyze(sources)

    assert result.total_files == 2
    assert result.analyzed_files == 2