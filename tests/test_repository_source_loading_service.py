from pathlib import Path

import pytest

from appy.application.language_parser import ParsedSource
from appy.application.repository_source_loading_service import (
    RepositorySourceLoadingError,
    RepositorySourceLoadingService,
)


@pytest.fixture
def repository(tmp_path):
    (tmp_path / "appy.py").write_text(
        "def main():\n    return 'hello'\n",
        encoding="utf-8",
    )
    (tmp_path / "service.py").write_text(
        "class Service:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Example repository\n",
        encoding="utf-8",
    )
    (tmp_path / "script.js").write_text(
        "function main() { return true; }\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def metadata():
    return [
        {
            "relative_path": "appy.py",
            "extension": ".py",
            "language": "Python",
        },
        {
            "relative_path": "service.py",
            "extension": ".py",
            "language": "Python",
        },
        {
            "relative_path": "README.md",
            "extension": ".md",
            "language": "Markdown",
        },
        {
            "relative_path": "script.js",
            "extension": ".js",
            "language": "JavaScript",
        },
    ]


@pytest.fixture
def service():
    return RepositorySourceLoadingService()


def test_constructor_creates_default_dependencies():
    service = RepositorySourceLoadingService()

    assert service.source_file_selection_service is not None
    assert service.language_parser_factory is not None


def test_constructor_accepts_custom_file_size_limit():
    service = RepositorySourceLoadingService(
        max_file_size_bytes=500
    )

    assert service.max_file_size_bytes == 500


@pytest.mark.parametrize("invalid_limit", [0, -1, True, 1.5, "100"])
def test_constructor_rejects_invalid_file_size_limit(invalid_limit):
    with pytest.raises(RepositorySourceLoadingError):
        RepositorySourceLoadingService(
            max_file_size_bytes=invalid_limit
        )


def test_load_and_parse_returns_result(repository, metadata, service):
    result = service.load_and_parse(repository, metadata)

    assert result.repository_path == str(repository.resolve())
    assert result.selected_file_count == 3
    assert result.parsed_file_count == 2
    assert result.skipped_file_count == 1
    assert result.is_successful is True


def test_loads_source_contents(repository, metadata, service):
    result = service.load_and_parse(repository, metadata)

    assert "appy.py" in result.source_files
    assert "def main" in result.source_files["appy.py"]
    assert "service.py" in result.source_files


def test_parses_python_sources(repository, metadata, service):
    result = service.load_and_parse(repository, metadata)

    assert isinstance(result.parsed_sources["appy.py"], ParsedSource)
    assert isinstance(result.parsed_sources["service.py"], ParsedSource)
    assert result.parsed_sources["appy.py"].language == "Python"


def test_preserves_repository_relative_paths(repository, metadata, service):
    result = service.load_and_parse(repository, metadata)

    assert set(result.source_files) == {"appy.py", "service.py", "script.js"}
    assert set(result.parsed_sources) == {"appy.py", "service.py"}


def test_reports_unregistered_parser(repository, metadata, service):
    result = service.load_and_parse(repository, metadata)

    parser_failures = [
        failure
        for failure in result.failures
        if failure.stage == "parser_lookup"
    ]

    assert len(parser_failures) == 1
    assert parser_failures[0].filename == "script.js"
    assert parser_failures[0].language == "JavaScript"


def test_language_filter_selects_only_requested_language(
    repository,
    metadata,
    service,
):
    result = service.load_and_parse(
        repository,
        metadata,
        languages=["Python"],
    )

    assert result.selected_file_count == 2
    assert result.parsed_file_count == 2
    assert set(result.parsed_sources) == {"appy.py", "service.py"}


def test_language_filter_accepts_single_string(
    repository,
    metadata,
    service,
):
    result = service.load_and_parse(
        repository,
        metadata,
        languages="Python",
    )

    assert result.parsed_file_count == 2


def test_reports_syntax_errors_without_stopping_other_files(
    repository,
    metadata,
    service,
):
    (repository / "appy.py").write_text(
        "def broken(:\n    pass\n",
        encoding="utf-8",
    )

    result = service.load_and_parse(repository, metadata)

    assert "appy.py" not in result.parsed_sources
    assert "service.py" in result.parsed_sources
    assert any(
        failure.filename == "appy.py" and failure.stage == "parsing"
        for failure in result.failures
    )


def test_reports_missing_source_file(repository, metadata, service):
    (repository / "service.py").unlink()

    result = service.load_and_parse(repository, metadata)

    assert "service.py" not in result.source_files
    assert any(
        failure.filename == "service.py" and failure.stage == "loading"
        for failure in result.failures
    )


def test_rejects_nonexistent_repository_path(metadata, service, tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(RepositorySourceLoadingError) as exc_info:
        service.load_and_parse(missing, metadata)

    assert exc_info.value.stage == "input_validation"


def test_rejects_file_as_repository_path(metadata, service, tmp_path):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(RepositorySourceLoadingError):
        service.load_and_parse(file_path, metadata)


@pytest.mark.parametrize(
    "invalid_path",
    [None, "", "   ", 123],
)
def test_rejects_invalid_repository_path(invalid_path, metadata, service):
    with pytest.raises(RepositorySourceLoadingError):
        service.load_and_parse(invalid_path, metadata)


def test_rejects_absolute_source_path(repository, service):
    absolute_file = repository / "appy.py"
    metadata = [
        {
            "relative_path": str(absolute_file),
            "extension": ".py",
            "language": "Python",
        }
    ]

    result = service.load_and_parse(repository, metadata)

    assert result.parsed_file_count == 0
    assert result.failures[0].stage == "loading"


def test_rejects_path_traversal(repository, service, tmp_path):
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("print('outside')", encoding="utf-8")

    metadata = [
        {
            "relative_path": "../outside.py",
            "extension": ".py",
            "language": "Python",
        }
    ]

    result = service.load_and_parse(repository, metadata)

    assert result.parsed_file_count == 0
    assert result.failures[0].stage == "loading"


def test_reports_file_larger_than_configured_limit(
    repository,
    metadata,
):
    service = RepositorySourceLoadingService(
        max_file_size_bytes=5
    )

    result = service.load_and_parse(repository, metadata)

    assert result.parsed_file_count == 0
    assert any(
        failure.stage == "loading"
        and "size limit" in failure.reason
        for failure in result.failures
    )


def test_uses_language_from_file_metadata(repository, service):
    metadata = [
        {
            "relative_path": "appy.py",
            "extension": ".py",
            "language": "UnknownLanguage",
        }
    ]

    result = service.load_and_parse(repository, metadata)

    assert result.parsed_file_count == 0
    assert result.failures[0].stage == "parser_lookup"


def test_detects_language_from_extension_when_missing(
    repository,
    service,
):
    metadata = [
        {
            "relative_path": "appy.py",
            "extension": ".py",
        }
    ]

    result = service.load_and_parse(repository, metadata)

    assert result.parsed_file_count == 1
    assert result.parsed_sources["appy.py"].language == "Python"


def test_returns_language_counts(repository, metadata, service):
    result = service.load_and_parse(repository, metadata)

    assert result.language_counts["Python"] == 2
    assert result.language_counts["JavaScript"] == 1


def test_failure_count_matches_failure_records(
    repository,
    metadata,
    service,
):
    result = service.load_and_parse(repository, metadata)

    assert result.failed_file_count == len(result.failures)


def test_result_is_not_successful_when_no_parser_is_available(
    repository,
    service,
):
    metadata = [
        {
            "relative_path": "script.js",
            "extension": ".js",
            "language": "JavaScript",
        }
    ]

    result = service.load_and_parse(repository, metadata)

    assert result.is_successful is False
    assert result.parsed_file_count == 0


def test_accepts_path_object(repository, metadata, service):
    result = service.load_and_parse(Path(repository), metadata)

    assert result.parsed_file_count == 2


def test_handles_empty_metadata(repository, service):
    result = service.load_and_parse(repository, [])

    assert result.selected_file_count == 0
    assert result.parsed_file_count == 0
    assert result.is_successful is False