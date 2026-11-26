
import pytest

from appy.application.code_duplication_detection_service import (
    CodeDuplicationDetectionError,
    CodeDuplicationDetectionResult,
    CodeDuplicationDetectionService,
    CodeOccurrence,
    DuplicateCodeBlock,
    DuplicationSeverity,
    DuplicationType,
    FileDuplicationResult,
)


@pytest.fixture
def service():
    return CodeDuplicationDetectionService()


def repeated_code():
    return (
        "def calculate_total(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )


def test_service_initializes_with_defaults(service):
    assert service.minimum_lines == 5
    assert service.minimum_occurrences == 2
    assert service.high_duplicate_lines == 20
    assert service.medium_duplicate_lines == 10


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_lines": 0},
        {"minimum_occurrences": 0},
        {"high_duplicate_lines": 0},
        {"medium_duplicate_lines": 0},
        {"minimum_lines": True},
    ],
)
def test_invalid_thresholds_are_rejected(kwargs):
    with pytest.raises(CodeDuplicationDetectionError):
        CodeDuplicationDetectionService(**kwargs)


def test_high_threshold_must_not_be_below_medium():
    with pytest.raises(CodeDuplicationDetectionError):
        CodeDuplicationDetectionService(
            high_duplicate_lines=5,
            medium_duplicate_lines=10,
        )


def test_empty_repository(service):
    result = service.analyze({})

    assert result.total_files == 0
    assert result.analyzed_files == 0
    assert result.skipped_files == 0
    assert result.total_lines == 0
    assert result.duplicated_lines == 0
    assert result.duplication_percentage == 0
    assert result.duplicate_blocks == ()
    assert result.has_duplicates is False


def test_analyze_requires_mapping(service):
    with pytest.raises(CodeDuplicationDetectionError):
        service.analyze("invalid")


def test_source_content_must_be_string(service):
    with pytest.raises(CodeDuplicationDetectionError):
        service.analyze({"module.py": 123})


@pytest.mark.parametrize(
    "path",
    [
        "",
        "../outside.py",
        "/absolute/module.py",
        "./module.py",
        "folder//module.py",
        "C:\\outside\\module.py",
    ],
)
def test_invalid_source_paths_are_rejected(service, path):
    with pytest.raises(CodeDuplicationDetectionError):
        service.analyze({path: "pass"})


def test_duplicate_normalized_paths_are_rejected(service):
    with pytest.raises(CodeDuplicationDetectionError):
        service.analyze(
            {
                "folder\\module.py": "pass",
                "folder/module.py": "pass",
            }
        )


def test_non_source_files_are_skipped(service):
    result = service.analyze(
        {
            "README.md": repeated_code(),
            "module.py": repeated_code(),
            "settings.json": "{}",
        }
    )

    assert result.total_files == 3
    assert result.analyzed_files == 1
    assert result.skipped_files == 2


def test_python_source_files_are_analyzed(service):
    result = service.analyze({"module.py": repeated_code()})

    assert result.analyzed_files == 1
    assert result.total_files == 1


def test_pythonw_files_are_supported(service):
    result = service.analyze({"module.pyw": repeated_code()})

    assert result.analyzed_files == 1


@pytest.mark.parametrize(
    "extension",
    [".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".go", ".rs"],
)
def test_supported_source_extensions_are_analyzed(service, extension):
    result = service.analyze(
        {f"module{extension}": repeated_code()}
    )

    assert result.analyzed_files == 1
    assert result.skipped_files == 0


def test_non_duplicate_code_produces_no_blocks(service):
    source = (
        "def first():\n"
        "    return 1\n"
        "\n"
        "def second():\n"
        "    return 2\n"
    )

    result = service.analyze({"module.py": source})

    assert result.has_duplicates is False
    assert result.duplicate_block_count == 0


def test_identical_code_across_two_files_is_detected(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert result.has_duplicates is True
    assert result.duplicate_block_count >= 1
    assert all(len(block.occurrences) >= 2 for block in result.duplicate_blocks)


def test_duplicate_block_contains_file_locations(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    block = result.duplicate_blocks[0]
    paths = {item.file_path for item in block.occurrences}

    assert paths == {"first.py", "second.py"}


def test_duplicate_occurrence_contains_line_ranges(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    occurrence = result.duplicate_blocks[0].occurrences[0]

    assert occurrence.start_line >= 1
    assert occurrence.end_line >= occurrence.start_line


def test_duplicate_code_is_normalized_for_indentation(service):
    first = (
        "def calculate_total(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )
    second = (
        "def calculate_total(items):\n"
        "        total = 0\n"
        "        for item in items:\n"
        "                total += item\n"
        "        return total\n"
    )

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    assert result.has_duplicates is True


def test_python_comments_do_not_prevent_duplicate_detection(service):
    first = (
        "def calculate_total(items):\n"
        "    # First implementation\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )
    second = (
        "def calculate_total(items):\n"
        "    # Another comment\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    assert result.has_duplicates is True


def test_python_docstrings_do_not_prevent_duplicate_detection(service):
    first = (
        '"""First module."""\n'
        "def calculate_total(items):\n"
        '    """First description."""\n'
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )
    second = (
        '"""Second module."""\n'
        "def calculate_total(items):\n"
        '    """Second description."""\n'
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    assert result.has_duplicates is True




def test_blank_lines_are_not_counted_as_duplicated_lines(service):
    first = (
        "def calculate_total(items):\n"
        "\n"
        "    total = 0\n"
        "    for item in items:\n"
        "\n"
        "        total += item\n"
        "    return total\n"
    )

    second = repeated_code()

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    first_result = next(
        item for item in result.file_results
        if item.file_path == "first.py"
    )

    assert first_result.duplicated_lines <= first_result.total_lines
    assert first_result.duplication_percentage <= 100
    assert result.duplicated_lines <= result.total_lines
    assert result.duplication_percentage <= 100




def test_blank_lines_do_not_prevent_duplicate_detection(service):
    first = (
        "def calculate_total(items):\n"
        "\n"
        "    total = 0\n"
        "    for item in items:\n"
        "\n"
        "        total += item\n"
        "    return total\n"
    )
    second = repeated_code()

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    assert result.has_duplicates is True


def test_duplicate_code_with_different_identifiers_is_not_exact(service):
    first = repeated_code()
    second = (
        "def calculate_sum(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    assert result.has_duplicates is False


def test_different_code_lengths_do_not_match(service):
    first = repeated_code()
    second = (
        "def calculate_total(items):\n"
        "    total = 0\n"
        "    return total\n"
    )

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    assert result.has_duplicates is False


def test_minimum_line_threshold_is_respected():
    configured = CodeDuplicationDetectionService(minimum_lines=6)

    result = configured.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert result.has_duplicates is False


def test_short_duplicate_threshold_detects_smaller_blocks():
    configured = CodeDuplicationDetectionService(minimum_lines=3)
    source = (
        "def calculate_total(items):\n"
        "    total = 0\n"
        "    return total\n"
    )

    result = configured.analyze(
        {"first.py": source, "second.py": source}
    )

    assert result.has_duplicates is True


def test_minimum_occurrences_threshold_is_respected():
    configured = CodeDuplicationDetectionService(
        minimum_lines=5,
        minimum_occurrences=3,
    )

    result = configured.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert result.has_duplicates is False


def test_three_occurrences_are_detected_when_required():
    configured = CodeDuplicationDetectionService(
        minimum_lines=5,
        minimum_occurrences=3,
    )

    result = configured.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
            "third.py": repeated_code(),
        }
    )

    assert result.has_duplicates is True
    assert all(
        len(block.occurrences) >= 3
        for block in result.duplicate_blocks
    )


def test_duplicate_blocks_have_exact_type(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert all(
        block.duplication_type == DuplicationType.EXACT
        for block in result.duplicate_blocks
    )


def test_duplicate_block_contains_normalized_code(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    block = result.duplicate_blocks[0]

    assert isinstance(block.normalized_code, tuple)
    assert len(block.normalized_code) == block.line_count
    assert block.line_count >= service.minimum_lines


def test_duplicate_ids_are_unique(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    ids = [block.duplicate_id for block in result.duplicate_blocks]

    assert len(ids) == len(set(ids))


def test_duplicate_block_severity_is_low_for_small_blocks():
    configured = CodeDuplicationDetectionService(
        minimum_lines=5,
        medium_duplicate_lines=10,
        high_duplicate_lines=20,
    )

    result = configured.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert all(
        block.severity == DuplicationSeverity.LOW
        for block in result.duplicate_blocks
    )


def test_duplicate_block_severity_is_medium_for_medium_blocks():
    configured = CodeDuplicationDetectionService(
        minimum_lines=5,
        medium_duplicate_lines=5,
        high_duplicate_lines=10,
    )

    result = configured.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert all(
        block.severity == DuplicationSeverity.MEDIUM
        for block in result.duplicate_blocks
    )


def test_duplicate_block_severity_is_high_for_large_blocks():
    configured = CodeDuplicationDetectionService(
        minimum_lines=5,
        medium_duplicate_lines=5,
        high_duplicate_lines=5,
    )

    result = configured.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert all(
        block.severity == DuplicationSeverity.HIGH
        for block in result.duplicate_blocks
    )


def test_high_severity_blocks_property(service):
    configured = CodeDuplicationDetectionService(
        minimum_lines=5,
        medium_duplicate_lines=5,
        high_duplicate_lines=5,
    )

    result = configured.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert len(result.high_severity_blocks) >= 1


def test_repository_duplication_percentage_is_calculated(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert 0 <= result.duplication_percentage <= 100
    assert result.duplicated_lines > 0


def test_file_level_results_are_created(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert len(result.file_results) == 2
    assert {item.file_path for item in result.file_results} == {
        "first.py", "second.py"
    }


def test_file_duplication_percentage_is_valid(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    for file_result in result.file_results:
        assert 0 <= file_result.duplication_percentage <= 100
        assert file_result.duplicated_lines <= file_result.total_lines


def test_file_block_count_is_reported(service):
    result = service.analyze(
        {
            "first.py": repeated_code(),
            "second.py": repeated_code(),
        }
    )

    assert all(
        item.duplicate_block_count > 0
        for item in result.file_results
    )


def test_empty_source_files_have_zero_duplication(service):
    result = service.analyze(
        {
            "first.py": "",
            "second.py": "",
        }
    )

    assert result.total_lines == 0
    assert result.duplicated_lines == 0
    assert result.duplication_percentage == 0


def test_single_file_with_repeated_block_detects_duplication(service):
    source = (
        "def first(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
        "\n"
        "def second(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )

    result = service.analyze({"module.py": source})

    assert result.has_duplicates is False
    assert all(
        len({item.file_path for item in block.occurrences}) == 1
        for block in result.duplicate_blocks
    )


def test_file_results_are_sorted(service):
    result = service.analyze(
        {
            "z.py": repeated_code(),
            "a.py": repeated_code(),
        }
    )

    assert [item.file_path for item in result.file_results] == [
        "a.py", "z.py"
    ]


def test_total_lines_counts_non_blank_lines(service):
    source = (
        "def example():\n"
        "\n"
        "    value = 1\n"
        "    return value\n"
    )

    result = service.analyze({"module.py": source})

    assert result.total_lines == 3


def test_python_syntax_error_does_not_crash_detection(service):
    source = (
        "def broken(\n"
        "    return 1\n"
    )

    result = service.analyze({"broken.py": source})

    assert result.analyzed_files == 1
    assert result.has_duplicates is False


def test_comment_only_lines_are_ignored_for_python(service):
    first = (
        "# First comment\n"
        "def calculate_total(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )
    second = (
        "# Different comment\n"
        "def calculate_total(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        total += item\n"
        "    return total\n"
    )

    result = service.analyze(
        {"first.py": first, "second.py": second}
    )

    assert result.has_duplicates is True


def test_result_model_reports_has_duplicates():
    result = CodeDuplicationDetectionResult(
        total_files=0,
        analyzed_files=0,
        skipped_files=0,
        total_lines=0,
        duplicated_lines=0,
        duplication_percentage=0,
        duplicate_block_count=0,
        duplicate_blocks=(),
        file_results=(),
    )

    assert result.has_duplicates is False


def test_occurrence_model_rejects_invalid_start_line():
    with pytest.raises(ValueError):
        CodeOccurrence(
            file_path="module.py",
            start_line=0,
            end_line=2,
        )


def test_occurrence_model_rejects_invalid_end_line():
    with pytest.raises(ValueError):
        CodeOccurrence(
            file_path="module.py",
            start_line=3,
            end_line=2,
        )


def test_duplicate_block_requires_two_occurrences():
    with pytest.raises(ValueError):
        DuplicateCodeBlock(
            duplicate_id="DUP-0001",
            duplication_type=DuplicationType.EXACT,
            normalized_code=("a", "b", "c", "d", "e"),
            line_count=5,
            occurrences=(
                CodeOccurrence("module.py", 1, 5),
            ),
            severity=DuplicationSeverity.LOW,
        )


def test_duplicate_block_rejects_invalid_type():
    with pytest.raises(TypeError):
        DuplicateCodeBlock(
            duplicate_id="DUP-0001",
            duplication_type="exact",
            normalized_code=("a", "b", "c", "d", "e"),
            line_count=5,
            occurrences=(
                CodeOccurrence("first.py", 1, 5),
                CodeOccurrence("second.py", 1, 5),
            ),
            severity=DuplicationSeverity.LOW,
        )


def test_file_result_rejects_duplicated_lines_above_total():
    with pytest.raises(ValueError):
        FileDuplicationResult(
            file_path="module.py",
            total_lines=5,
            duplicated_lines=6,
            duplication_percentage=100,
            duplicate_block_count=1,
        )


def test_result_rejects_inconsistent_file_counts():
    with pytest.raises(ValueError):
        CodeDuplicationDetectionResult(
            total_files=3,
            analyzed_files=1,
            skipped_files=1,
            total_lines=10,
            duplicated_lines=0,
            duplication_percentage=0,
            duplicate_block_count=0,
            duplicate_blocks=(),
            file_results=(),
        )


def test_result_rejects_invalid_percentage():
    with pytest.raises(ValueError):
        CodeDuplicationDetectionResult(
            total_files=0,
            analyzed_files=0,
            skipped_files=0,
            total_lines=0,
            duplicated_lines=0,
            duplication_percentage=101,
            duplicate_block_count=0,
            duplicate_blocks=(),
            file_results=(),
        )
