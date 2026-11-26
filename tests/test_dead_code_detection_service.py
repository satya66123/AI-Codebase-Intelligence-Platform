
"""Tests for the dead-code detection service."""

import pytest

from appy.application.dead_code_detection_service import (
    DeadCodeDetectionError,
    DeadCodeDetectionResult,
    DeadCodeDetectionService,
    DeadCodeFileResult,
    DeadCodeFinding,
    DeadCodeSeverity,
    DeadCodeType,
)


@pytest.fixture
def service():
    return DeadCodeDetectionService()


def test_empty_repository_returns_empty_result(service):
    result = service.analyze({})

    assert isinstance(result, DeadCodeDetectionResult)
    assert result.total_files == 0
    assert result.analyzed_files == 0
    assert result.skipped_files == 0
    assert result.total_findings == 0
    assert result.has_dead_code is False


def test_non_mapping_input_is_rejected(service):
    with pytest.raises(DeadCodeDetectionError):
        service.analyze(["main.py", "source"])


@pytest.mark.parametrize("path", ["", " ", None, 123, "../main.py", "/main.py", "C:\\main.py", "src/../main.py", "./main.py", "src//main.py"])
def test_invalid_paths_are_rejected(service, path):
    with pytest.raises(DeadCodeDetectionError):
        service.analyze({path: "print('hello')"})


def test_non_string_source_is_rejected(service):
    with pytest.raises(DeadCodeDetectionError):
        service.analyze({"main.py": None})


def test_duplicate_normalized_paths_are_rejected(service):
    with pytest.raises(DeadCodeDetectionError):
        service.analyze({
            "src\\main.py": "print('a')",
            "src/main.py": "print('b')",
        })


def test_unsupported_files_are_skipped(service):
    result = service.analyze({
        "main.py": "print('hello')",
        "README.md": "# Project",
        "appy.js": "console.log('hello');",
    })

    assert result.total_files == 3
    assert result.analyzed_files == 1
    assert result.skipped_files == 2
    assert len(result.file_results) == 1
    assert result.file_results[0].file_path == "main.py"


def test_python_file_is_analyzed(service):
    result = service.analyze({"main.py": "print('hello')\n"})

    assert result.analyzed_files == 1
    assert result.file_results[0].analyzed is True
    assert result.file_results[0].syntax_error == ""


def test_syntax_error_is_reported_without_crashing(service):
    result = service.analyze({"broken.py": "def broken(:\n    pass\n"})

    assert result.analyzed_files == 1
    assert result.syntax_error_count == 1
    assert result.file_results[0].analyzed is False
    assert result.file_results[0].syntax_error
    assert result.file_results[0].findings == ()


def test_public_function_is_not_reported_by_default(service):
    result = service.analyze({
        "main.py": "def calculate():\n    return 10\n"
    })

    assert not any(
        item.code_type == DeadCodeType.UNUSED_FUNCTION
        for item in result.findings
    )


def test_unused_private_function_is_reported(service):
    result = service.analyze({
        "main.py": "def _unused_helper():\n    return 10\n"
    })

    finding = next(
        item for item in result.findings
        if item.code_type == DeadCodeType.UNUSED_FUNCTION
    )

    assert finding.symbol == "_unused_helper"
    assert finding.line == 1
    assert finding.severity == DeadCodeSeverity.MEDIUM


def test_private_function_with_reference_is_not_reported(service):
    source = (
        "def _helper():\n"
        "    return 10\n"
        "\n"
        "def run():\n"
        "    return _helper()\n"
    )

    result = service.analyze({"main.py": source})

    assert not any(
        item.symbol == "_helper"
        and item.code_type == DeadCodeType.UNUSED_FUNCTION
        for item in result.findings
    )


def test_unused_private_class_is_reported(service):
    result = service.analyze({
        "main.py": "class _UnusedService:\n    pass\n"
    })

    finding = next(
        item for item in result.findings
        if item.code_type == DeadCodeType.UNUSED_CLASS
    )

    assert finding.symbol == "_UnusedService"
    assert finding.line == 1


def test_referenced_private_class_is_not_reported(service):
    source = (
        "class _Service:\n"
        "    pass\n"
        "\n"
        "def create():\n"
        "    return _Service()\n"
    )

    result = service.analyze({"main.py": source})

    assert not any(
        item.symbol == "_Service"
        and item.code_type == DeadCodeType.UNUSED_CLASS
        for item in result.findings
    )


def test_dunder_function_is_not_reported(service):
    result = service.analyze({
        "main.py": "def __init__():\n    pass\n"
    })

    assert not any(
        item.symbol == "__init__"
        for item in result.findings
    )


def test_public_symbols_can_be_included():
    service = DeadCodeDetectionService(include_public_symbols=True)
    result = service.analyze({
        "main.py": "def unused_function():\n    return 1\n"
    })

    assert any(
        item.symbol == "unused_function"
        and item.code_type == DeadCodeType.UNUSED_FUNCTION
        for item in result.findings
    )


def test_exported_private_function_is_not_reported(service):
    source = (
        "__all__ = ['_public_api']\n"
        "\n"
        "def _public_api():\n"
        "    return 1\n"
    )

    result = service.analyze({"main.py": source})

    assert not any(
        item.symbol == "_public_api"
        for item in result.findings
    )


def test_unused_import_is_reported(service):
    result = service.analyze({
        "main.py": "import os\n"
    })

    finding = next(
        item for item in result.findings
        if item.code_type == DeadCodeType.UNUSED_IMPORT
    )

    assert finding.symbol == "os"
    assert finding.line == 1
    assert finding.severity == DeadCodeSeverity.LOW


def test_used_import_is_not_reported(service):
    result = service.analyze({
        "main.py": "import os\nprint(os.getcwd())\n"
    })

    assert not any(
        item.code_type == DeadCodeType.UNUSED_IMPORT
        for item in result.findings
    )


def test_unused_from_import_is_reported(service):
    result = service.analyze({
        "main.py": "from pathlib import Path\n"
    })

    finding = next(
        item for item in result.findings
        if item.code_type == DeadCodeType.UNUSED_IMPORT
    )

    assert finding.symbol == "Path"


def test_used_from_import_is_not_reported(service):
    result = service.analyze({
        "main.py": "from pathlib import Path\nprint(Path('.'))\n"
    })

    assert not any(
        item.code_type == DeadCodeType.UNUSED_IMPORT
        for item in result.findings
    )


def test_import_alias_is_checked_by_bound_name(service):
    result = service.analyze({
        "main.py": "import pathlib as paths\nprint(paths.Path('.'))\n"
    })

    assert not any(
        item.code_type == DeadCodeType.UNUSED_IMPORT
        for item in result.findings
    )


def test_unused_import_detection_can_be_disabled():
    service = DeadCodeDetectionService(detect_unused_imports=False)
    result = service.analyze({"main.py": "import os\n"})

    assert not any(
        item.code_type == DeadCodeType.UNUSED_IMPORT
        for item in result.findings
    )


def test_future_import_is_not_reported(service):
    result = service.analyze({
        "main.py": "from __future__ import annotations\n"
    })

    assert not any(
        item.code_type == DeadCodeType.UNUSED_IMPORT
        for item in result.findings
    )


def test_star_import_is_not_reported(service):
    result = service.analyze({
        "main.py": "from package import *\n"
    })

    assert not any(
        item.code_type == DeadCodeType.UNUSED_IMPORT
        for item in result.findings
    )


def test_statement_after_return_is_unreachable(service):
    source = (
        "def calculate():\n"
        "    return 10\n"
        "    print('unreachable')\n"
    )

    result = service.analyze({"main.py": source})

    finding = next(
        item for item in result.findings
        if item.code_type == DeadCodeType.UNREACHABLE_CODE
    )

    assert finding.line == 3
    assert finding.severity == DeadCodeSeverity.HIGH


def test_statement_after_raise_is_unreachable(service):
    source = (
        "def run():\n"
        "    raise RuntimeError('failure')\n"
        "    print('unreachable')\n"
    )

    result = service.analyze({"main.py": source})

    assert any(
        item.code_type == DeadCodeType.UNREACHABLE_CODE
        and item.line == 3
        for item in result.findings
    )


def test_statement_after_break_is_unreachable(service):
    source = (
        "for item in items:\n"
        "    break\n"
        "    print(item)\n"
    )

    result = service.analyze({"main.py": source})

    assert any(
        item.code_type == DeadCodeType.UNREACHABLE_CODE
        and item.line == 3
        for item in result.findings
    )


def test_statement_after_continue_is_unreachable(service):
    source = (
        "for item in items:\n"
        "    continue\n"
        "    print(item)\n"
    )

    result = service.analyze({"main.py": source})

    assert any(
        item.code_type == DeadCodeType.UNREACHABLE_CODE
        and item.line == 3
        for item in result.findings
    )


def test_code_after_if_with_both_branches_terminating_is_unreachable(service):
    source = (
        "def choose(value):\n"
        "    if value:\n"
        "        return 1\n"
        "    else:\n"
        "        return 2\n"
        "    print('unreachable')\n"
    )

    result = service.analyze({"main.py": source})

    assert any(
        item.code_type == DeadCodeType.UNREACHABLE_CODE
        and item.line == 6
        for item in result.findings
    )


def test_code_after_if_without_else_is_not_marked_unreachable(service):
    source = (
        "def choose(value):\n"
        "    if value:\n"
        "        return 1\n"
        "    print('reachable when false')\n"
    )

    result = service.analyze({"main.py": source})

    assert not any(
        item.code_type == DeadCodeType.UNREACHABLE_CODE
        and item.line == 4
        for item in result.findings
    )


def test_unreachable_detection_can_be_disabled():
    service = DeadCodeDetectionService(detect_unreachable_code=False)
    source = "def run():\n    return\n    print('unreachable')\n"

    result = service.analyze({"main.py": source})

    assert not any(
        item.code_type == DeadCodeType.UNREACHABLE_CODE
        for item in result.findings
    )


def test_multiple_files_are_analyzed_independently(service):
    result = service.analyze({
        "one.py": "import os\n",
        "two.py": "import sys\n",
    })

    assert result.analyzed_files == 2
    assert result.total_findings == 2
    assert {item.file_path for item in result.findings} == {
        "one.py",
        "two.py",
    }


def test_nested_python_paths_are_supported(service):
    result = service.analyze({
        "src/services/helper.py": "import os\n"
    })

    assert result.analyzed_files == 1
    assert result.file_results[0].file_path == "src/services/helper.py"


def test_findings_are_sorted_by_line(service):
    source = (
        "import os\n"
        "\n"
        "def _unused():\n"
        "    return 1\n"
    )

    result = service.analyze({"main.py": source})

    assert list(result.findings) == sorted(
        result.findings,
        key=lambda item: (
            item.line,
            item.end_line,
            item.code_type.value,
            item.symbol,
        ),
    )


def test_has_dead_code_is_true_when_findings_exist(service):
    result = service.analyze({"main.py": "import os\n"})

    assert result.has_dead_code is True


def test_has_dead_code_is_false_without_findings(service):
    result = service.analyze({
        "main.py": "def calculate():\n    return 10\n"
    })

    assert result.has_dead_code is False


def test_high_severity_findings_property(service):
    source = "def run():\n    return\n    print('unreachable')\n"
    result = service.analyze({"main.py": source})

    assert len(result.high_severity_findings) == 1
    assert result.high_severity_findings[0].severity == DeadCodeSeverity.HIGH


def test_findings_by_type_counts_all_types(service):
    source = (
        "import os\n"
        "\n"
        "def _unused():\n"
        "    return 1\n"
        "\n"
        "def run():\n"
        "    return\n"
        "    print('unreachable')\n"
    )

    result = service.analyze({"main.py": source})
    counts = result.findings_by_type

    assert counts[DeadCodeType.UNUSED_IMPORT] == 1
    assert counts[DeadCodeType.UNUSED_FUNCTION] == 1
    assert counts[DeadCodeType.UNREACHABLE_CODE] == 1
    assert counts[DeadCodeType.UNUSED_CLASS] == 0


def test_syntax_error_count_excludes_valid_files(service):
    result = service.analyze({
        "valid.py": "print('hello')\n",
        "invalid.py": "def broken(:\n",
    })

    assert result.syntax_error_count == 1
    assert result.analyzed_files == 2


def test_file_line_count_is_preserved(service):
    source = "import os\n\nprint('hello')\n"
    result = service.analyze({"main.py": source})

    assert result.file_results[0].total_lines == 3


def test_file_result_rejects_negative_line_count():
    with pytest.raises(ValueError):
        DeadCodeFileResult(
            file_path="main.py",
            total_lines=-1,
            analyzed=True,
            syntax_error="",
            findings=(),
        )


def test_file_result_requires_syntax_error_when_not_analyzed():
    with pytest.raises(ValueError):
        DeadCodeFileResult(
            file_path="main.py",
            total_lines=1,
            analyzed=False,
            syntax_error="",
            findings=(),
        )


def test_finding_rejects_invalid_line_range():
    with pytest.raises(ValueError):
        DeadCodeFinding(
            file_path="main.py",
            line=5,
            end_line=3,
            code_type=DeadCodeType.UNUSED_IMPORT,
            severity=DeadCodeSeverity.LOW,
            symbol="os",
            message="Unused import",
        )


def test_finding_rejects_invalid_code_type():
    with pytest.raises(TypeError):
        DeadCodeFinding(
            file_path="main.py",
            line=1,
            end_line=1,
            code_type="unused_import",
            severity=DeadCodeSeverity.LOW,
            symbol="os",
            message="Unused import",
        )


def test_result_rejects_inconsistent_file_counts():
    with pytest.raises(ValueError):
        DeadCodeDetectionResult(
            total_files=2,
            analyzed_files=1,
            skipped_files=0,
            total_findings=0,
            findings=(),
            file_results=(),
        )


def test_result_rejects_inconsistent_finding_count():
    with pytest.raises(ValueError):
        DeadCodeDetectionResult(
            total_files=0,
            analyzed_files=0,
            skipped_files=0,
            total_findings=1,
            findings=(),
            file_results=(),
        )


def test_analysis_does_not_modify_source_files(service):
    source = "import os\n"
    source_files = {"main.py": source}

    service.analyze(source_files)

    assert source_files["main.py"] == source


def test_analysis_is_deterministic(service):
    source_files = {
        "b.py": "import sys\n",
        "a.py": "import os\n",
    }

    first = service.analyze(source_files)
    second = service.analyze(source_files)

    assert first == second


@pytest.mark.parametrize(
    "option",
    [
        {"include_public_symbols": "yes"},
        {"detect_unused_imports": 1},
        {"detect_unreachable_code": None},
    ],
)
def test_invalid_configuration_is_rejected(option):
    with pytest.raises(DeadCodeDetectionError):
        DeadCodeDetectionService(**option)
