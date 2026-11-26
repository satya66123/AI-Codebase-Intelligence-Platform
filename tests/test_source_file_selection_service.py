
from dataclasses import dataclass

import pytest

from appy.application.source_file_selection_service import (
    SourceFileSelectionError,
    SourceFileSelectionService,
)

@pytest.fixture
def service():
    return SourceFileSelectionService()

@pytest.fixture
def sample_files():
    return [
        {
            "name": "main.py",
            "relative_path": "appy/main.py",
            "extension": ".py",
            "language": "Python",
        },
        {
            "name": "appy.js",
            "relative_path": "frontend/appy.js",
            "extension": ".js",
            "language": "JavaScript",
        },
        {
            "name": "README.md",
            "relative_path": "README.md",
            "extension": ".md",
            "language": "Markdown",
        },
        {
            "name": "config.json",
            "relative_path": "config.json",
            "extension": ".json",
            "language": "JSON",
        },
        {
            "name": "service.java",
            "relative_path": "src/service.java",
            "extension": ".java",
            "language": "Java",
        },
    ]

def test_select_supported_source_files(
    service,
    sample_files,
):
    result = service.select_source_files(sample_files)

    assert result.selected_count == 3
    assert result.total_files == 5
    assert result.skipped_count == 2

def test_select_source_files_by_language(
    service,
    sample_files,
):
    result = service.select_source_files(
        sample_files,
        languages=["Python"],
    )

    assert result.selected_count == 1
    assert result.files[0]["name"] == "main.py"

def test_select_multiple_languages(
    service,
    sample_files,
):
    result = service.select_source_files(
        sample_files,
        languages=["Python", "Java"],
    )

    assert result.selected_count == 2

def test_language_statistics(
    service,
    sample_files,
):
    result = service.select_source_files(sample_files)

    assert result.languages == {
        "Python": 1,
        "JavaScript": 1,
        "Java": 1,
    }

def test_unsupported_files_are_skipped(service):
    files = [
        {"name": "image.png", "extension": ".png"},
        {"name": "document.pdf", "extension": ".pdf"},
    ]

    result = service.select_source_files(files)

    assert result.selected_count == 0
    assert result.skipped_count == 2

def test_extension_is_detected_from_relative_path(service):
    files = [
        {
            "name": "main.py",
            "relative_path": "src/main.py",
            "extension": "",
        }
    ]

    result = service.select_source_files(files)

    assert result.selected_count == 1

def test_extension_matching_is_case_insensitive(service):
    files = [
        {"name": "main.PY", "extension": ".PY"}
    ]

    result = service.select_source_files(files)

    assert result.selected_count == 1

def test_empty_file_list(service):
    result = service.select_source_files([])

    assert result.total_files == 0
    assert result.selected_count == 0
    assert result.skipped_count == 0

def test_none_file_list_rejected(service):
    with pytest.raises(SourceFileSelectionError):
        service.select_source_files(None)

def test_invalid_language_filter_rejected(
    service,
    sample_files,
):
    with pytest.raises(SourceFileSelectionError):
        service.select_source_files(
            sample_files,
            languages=["", "  "],
        )

def test_dataclass_file_metadata_supported(service):

    @dataclass
    class FileRecord:
        name: str
        relative_path: str
        extension: str
        language: str

    files = [
        FileRecord(
            name="main.py",
            relative_path="appy/main.py",
            extension=".py",
            language="Python",
        )
    ]

    result = service.select_source_files(files)

    assert result.selected_count == 1
    assert result.files[0].name == "main.py"