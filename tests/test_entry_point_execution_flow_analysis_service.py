
import ast
from pathlib import Path

import pytest

from appy.application.entry_point_execution_flow_analysis_service import (
    EntryPointExecutionFlowAnalysisService,
    EntryPointExecutionFlowError,
    EntryPointType,
)
from appy.application.language_parser import ParsedSource
from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import RepositoryScanResult


@pytest.fixture
def repository(tmp_path):
    return RepositoryInfo(
        root=tmp_path,
        name=tmp_path.name,
        is_git_repository=False,
    )


@pytest.fixture
def service():
    return EntryPointExecutionFlowAnalysisService()


def create_scan(root, *files):
    paths = []

    for filename in files:
        file_path = root / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("# source\n", encoding="utf-8")
        paths.append(file_path)

    return RepositoryScanResult(
        root=root,
        files=tuple(paths),
        directories=tuple(
            sorted(
                {
                    parent
                    for path in paths
                    for parent in path.parents
                    if parent != root and root in parent.parents
                }
            )
        ),
        symlinks=(),
    )


def parsed(source, filename):
    return ParsedSource(
        language="python",
        filename=filename,
        tree=ast.parse(source),
        line_count=len(source.splitlines()),
    )


def test_analyze_empty_repository(service, repository):
    scan = RepositoryScanResult(
        root=repository.root,
        files=(),
        directories=(),
        symlinks=(),
    )

    result = service.analyze(repository, scan, {})

    assert result.repository_name == repository.name
    assert result.total_repository_files == 0
    assert result.analyzed_python_files == 0
    assert result.total_entry_points == 0
    assert result.entry_points == ()
    assert result.traces == ()


def test_detects_main_guard(service, repository):
    source = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.confirmed_entry_points == 1
    assert result.total_entry_points == 1
    assert result.entry_points[0].confirmed is True
    assert result.entry_points[0].entry_point_type == (
        EntryPointType.MAIN_GUARD
    )


def test_detects_main_guard_line(service, repository):
    source = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.entry_points[0].line == 5


def test_detects_conventional_main_candidate(service, repository):
    source = """
def start():
    return 1
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.conventional_candidates == 1
    assert result.confirmed_entry_points == 0
    assert result.entry_points[0].confirmed is False
    assert result.entry_points[0].entry_point_type == (
        EntryPointType.CONVENTIONAL
    )


@pytest.mark.parametrize(
    "filename",
    [
        "appy.py",
        "run.py",
        "manage.py",
        "wsgi.py",
        "asgi.py",
        "__main__.py",
    ],
)
def test_detects_conventional_filenames(
    service,
    repository,
    filename,
):
    scan = create_scan(repository.root, filename)
    source = "def start():\n    return 1"

    result = service.analyze(
        repository,
        scan,
        {filename: parsed(source, filename)},
    )

    assert result.conventional_candidates == 1
    assert result.entry_points[0].file_path == filename


def test_main_guard_takes_precedence_over_filename_candidate(
    service,
    repository,
):
    source = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "appy.py")

    result = service.analyze(
        repository,
        scan,
        {"appy.py": parsed(source, "appy.py")},
    )

    assert result.total_entry_points == 1
    assert result.confirmed_entry_points == 1
    assert result.conventional_candidates == 0


def test_extracts_main_guard_function_calls(service, repository):
    source = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.entry_points[0].function_names == ("main.main",)


def test_detects_execution_steps(service, repository):
    source = """
def main():
    helper()

def helper():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.total_calls == 2
    assert result.execution_steps == 2
    assert len(result.execution_steps_records) == 2


def test_traces_execution_flow(service, repository):
    source = """
def main():
    first()

def first():
    second()

def second():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.traces
    assert any(
        trace.path == (
            "main",
            "main.first",
            "main.second",
        )
        for trace in result.traces
    )


def test_reports_no_confirmed_entry_point_for_unrecognized_file(
    service,
    repository,
):
    source = """
def helper():
    return 1
"""

    scan = create_scan(repository.root, "utilities.py")

    result = service.analyze(
        repository,
        scan,
        {"utilities.py": parsed(source, "utilities.py")},
    )

    assert result.total_entry_points == 0
    assert result.has_confirmed_entry_points is False


def test_does_not_confirm_conventional_candidate(service, repository):
    scan = create_scan(repository.root, "appy.py")
    source = "print('hello')"

    result = service.analyze(
        repository,
        scan,
        {"appy.py": parsed(source, "appy.py")},
    )

    assert result.has_confirmed_entry_points is False
    assert result.candidate_findings[0].confirmed is False


def test_supports_multiple_entry_points(service, repository):
    first = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""

    second = """
def start():
    return 2

if __name__ == "__main__":
    start()
"""

    scan = create_scan(
        repository.root,
        "main.py",
        "worker.py",
    )

    result = service.analyze(
        repository,
        scan,
        {
            "main.py": parsed(first, "main.py"),
            "worker.py": parsed(second, "worker.py"),
        },
    )

    assert result.confirmed_entry_points == 2
    assert result.total_entry_points == 2


def test_skips_non_python_parsed_source(service, repository):
    scan = create_scan(repository.root, "sample.js")

    source = ParsedSource(
        language="javascript",
        filename="sample.js",
        tree=ast.parse("pass"),
        line_count=1,
    )

    result = service.analyze(
        repository,
        scan,
        {"sample.js": source},
    )

    assert result.skipped_files == 1
    assert result.analyzed_python_files == 0


def test_rejects_invalid_repository(service):
    scan = RepositoryScanResult(
        root=Path("."),
        files=(),
        directories=(),
        symlinks=(),
    )

    with pytest.raises(EntryPointExecutionFlowError):
        service.analyze(None, scan, {})


def test_rejects_invalid_scan_result(service, repository):
    with pytest.raises(EntryPointExecutionFlowError):
        service.analyze(repository, None, {})


def test_rejects_invalid_parsed_sources(service, repository):
    scan = RepositoryScanResult(
        root=repository.root,
        files=(),
        directories=(),
        symlinks=(),
    )

    with pytest.raises(EntryPointExecutionFlowError):
        service.analyze(repository, scan, [])


@pytest.mark.parametrize(
    "max_depth",
    [0, -1, 1.5, True, "5"],
)
def test_rejects_invalid_max_depth(
    service,
    repository,
    max_depth,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=(),
        directories=(),
        symlinks=(),
    )

    with pytest.raises(EntryPointExecutionFlowError):
        service.analyze(
            repository,
            scan,
            {},
            max_depth=max_depth,
        )


def test_rejects_mismatched_repository_roots(service, tmp_path):
    repository = RepositoryInfo(
        root=tmp_path / "one",
        name="one",
        is_git_repository=False,
    )
    other_root = tmp_path / "two"
    other_root.mkdir()

    scan = RepositoryScanResult(
        root=other_root,
        files=(),
        directories=(),
        symlinks=(),
    )

    with pytest.raises(
        EntryPointExecutionFlowError,
        match="roots do not match",
    ):
        service.analyze(repository, scan, {})


def test_rejects_unscanned_source_file(service, repository):
    scan = create_scan(repository.root, "main.py")

    with pytest.raises(
        EntryPointExecutionFlowError,
        match="not found in the repository scan",
    ):
        service.analyze(
            repository,
            scan,
            {
                "missing.py": parsed(
                    "def main():\n    return 1",
                    "missing.py",
                )
            },
        )


def test_rejects_invalid_parsed_source(service, repository):
    scan = create_scan(repository.root, "main.py")

    with pytest.raises(EntryPointExecutionFlowError):
        service.analyze(
            repository,
            scan,
            {"main.py": "not parsed source"},
        )


def test_rejects_filename_mismatch(service, repository):
    scan = create_scan(repository.root, "main.py")

    with pytest.raises(
        EntryPointExecutionFlowError,
        match="does not match",
    ):
        service.analyze(
            repository,
            scan,
            {
                "main.py": parsed(
                    "def main():\n    return 1",
                    "other.py",
                )
            },
        )


def test_rejects_absolute_source_key(service, repository):
    scan = create_scan(repository.root, "main.py")
    absolute_key = str(repository.root / "main.py")

    with pytest.raises(EntryPointExecutionFlowError):
        service.analyze(
            repository,
            scan,
            {
                absolute_key: parsed(
                    "def main():\n    return 1",
                    absolute_key,
                )
            },
        )


def test_execution_steps_preserve_line_numbers(service, repository):
    source = """
def main():
    helper()

def helper():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert any(
        step.line == 3
        and step.caller == "main.main"
        and step.callee == "helper"
        for step in result.execution_steps_records
    )


def test_result_properties(service, repository):
    source = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.has_entry_points is True
    assert result.has_confirmed_entry_points is True
    assert result.confirmed_findings
    assert result.has_execution_flows is True
    assert result.maximum_trace_depth >= 0


def test_orders_confirmed_findings_before_candidates(
    service,
    repository,
):
    confirmed = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""

    candidate = """
def start():
    return 1
"""

    scan = create_scan(
        repository.root,
        "appy.py",
        "worker.py",
    )

    result = service.analyze(
        repository,
        scan,
        {
            "appy.py": parsed(candidate, "appy.py"),
            "worker.py": parsed(confirmed, "worker.py"),
        },
    )

    assert result.entry_points[0].confirmed is True
    assert result.entry_points[1].confirmed is False


def test_does_not_mutate_parsed_sources(service, repository):
    scan = create_scan(repository.root, "main.py")
    source = parsed(
        "def main():\n    return 1",
        "main.py",
    )
    sources = {"main.py": source}
    original = dict(sources)

    service.analyze(repository, scan, sources)

    assert sources == original


def test_handles_empty_main_guard_body(service, repository):
    source = """
if __name__ == "__main__":
    pass
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.confirmed_entry_points == 1
    assert result.entry_points[0].function_names == ()


def test_detects_recursive_execution_flow(service, repository):
    source = """
def first():
    second()

def second():
    first()

if __name__ == "__main__":
    first()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert any(trace.is_recursive for trace in result.traces)


def test_respects_maximum_trace_depth(service, repository):
    source = """
def main():
    first()

def first():
    second()

def second():
    third()

def third():
    return 1

if __name__ == "__main__":
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
        max_depth=1,
    )

    assert any(
        trace.terminated_by_depth_limit
        for trace in result.traces
    )


def test_ignores_main_guard_inside_function(service, repository):
    source = """
def helper():
    if __name__ == "__main__":
        return 1
"""

    scan = create_scan(repository.root, "utilities.py")

    result = service.analyze(
        repository,
        scan,
        {"utilities.py": parsed(source, "utilities.py")},
    )

    assert result.confirmed_entry_points == 0


def test_detects_reversed_main_guard_comparison(service, repository):
    source = """
def main():
    return 1

if "__main__" == __name__:
    main()
"""

    scan = create_scan(repository.root, "main.py")

    result = service.analyze(
        repository,
        scan,
        {"main.py": parsed(source, "main.py")},
    )

    assert result.confirmed_entry_points == 1
