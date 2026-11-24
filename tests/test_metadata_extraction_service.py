
import pytest

from app.application.repository_input import RepositoryInfo
from app.application.repository_scanner import RepositoryScanner
from app.application.metadata_extraction_service import (
    MetadataExtractionService,
    MetadataExtractionError,
)


def scan_repository(root):
    repository = RepositoryInfo(
        root=root,
        name=root.name,
        is_git_repository=False,
    )

    return RepositoryScanner().scan(repository)


def test_extract_python_file_metadata(tmp_path):
    file_path = tmp_path / "main.py"
    file_path.write_text("print('hello')")

    service = MetadataExtractionService()

    metadata = service.extract_file_metadata(
        file_path,
        tmp_path,
    )

    assert metadata.name == "main.py"
    assert metadata.relative_path == "main.py"
    assert metadata.extension == ".py"
    assert metadata.language == "Python"
    assert metadata.size_bytes == file_path.stat().st_size
    assert metadata.modified_time


def test_extract_nested_file_metadata(tmp_path):
    source = tmp_path / "src"
    source.mkdir()

    file_path = source / "app.js"
    file_path.write_text("console.log('hello')")

    metadata = MetadataExtractionService().extract_file_metadata(
        file_path,
        tmp_path,
    )

    assert metadata.relative_path == "src/app.js"
    assert metadata.language == "JavaScript"


def test_extract_repository_metadata(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "app.js").write_text("console.log('hello')")

    source = tmp_path / "src"
    source.mkdir()

    (source / "service.py").write_text("class Service: pass")

    result = scan_repository(tmp_path)

    metadata = MetadataExtractionService().extract_repository_metadata(
        result
    )

    assert metadata["repository_name"] == tmp_path.name
    assert metadata["total_files"] == 3
    assert metadata["total_directories"] == 1

    assert metadata["languages"] == {
        "JavaScript": 1,
        "Python": 2,
    }


def test_repository_total_size(tmp_path):
    (tmp_path / "main.py").write_text("12345")
    (tmp_path / "app.js").write_text("123")

    result = scan_repository(tmp_path)

    metadata = MetadataExtractionService().extract_repository_metadata(
        result
    )

    expected_size = sum(
        path.stat().st_size
        for path in result.files
    )

    assert metadata["total_size_bytes"] == expected_size


def test_empty_repository_metadata(tmp_path):
    result = scan_repository(tmp_path)

    metadata = MetadataExtractionService().extract_repository_metadata(
        result
    )

    assert metadata["total_files"] == 0
    assert metadata["total_directories"] == 0
    assert metadata["total_size_bytes"] == 0
    assert metadata["languages"] == {}
    assert metadata["files"] == []


def test_file_outside_repository_rejected(tmp_path):
    outside_file = tmp_path.parent / "outside.py"
    outside_file.write_text("print('outside')")

    service = MetadataExtractionService()

    with pytest.raises(MetadataExtractionError):
        service.extract_file_metadata(
            outside_file,
            tmp_path,
        )


def test_missing_file_rejected(tmp_path):
    missing_file = tmp_path / "missing.py"

    service = MetadataExtractionService()

    with pytest.raises(MetadataExtractionError):
        service.extract_file_metadata(
            missing_file,
            tmp_path,
        )


def test_invalid_scan_result_rejected():
    service = MetadataExtractionService()

    with pytest.raises(MetadataExtractionError):
        service.extract_repository_metadata("invalid")
