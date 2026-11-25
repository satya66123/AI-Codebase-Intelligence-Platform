
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from app.application.repository_input import RepositoryInfo
from app.application.repository_scanner import RepositoryScanResult
from app.application.metadata_extraction_service import FileMetadata
from app.application.repository_metadata_validation_service import (
    RepositoryMetadataValidationError,
    RepositoryMetadataIssue,
    RepositoryMetadataValidationResult,
    RepositoryMetadataValidationService,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def repository(tmp_path):
    """Create a repository containing representative files."""
    (tmp_path / "README.md").write_text(
        "# Repository",
        encoding="utf-8",
    )

    app_directory = tmp_path / "app"
    app_directory.mkdir()

    (app_directory / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    (app_directory / "utils.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )

    return RepositoryInfo(
        root=tmp_path,
        name=tmp_path.name,
        is_git_repository=False,
    )


@pytest.fixture
def scan_result(repository):
    """Create a scan result for the repository."""
    return RepositoryScanResult(
        root=repository.root,
        files=(
            repository.root / "README.md",
            repository.root / "app" / "main.py",
            repository.root / "app" / "utils.py",
        ),
        directories=(
            repository.root / "app",
        ),
        symlinks=(),
    )


@pytest.fixture
def service():
    return RepositoryMetadataValidationService()


def make_file_metadata(
    file_path,
    repository_root,
    language="Python",
    name=None,
    relative_path=None,
    extension=None,
    size_bytes=None,
    modified_time=None,
):
    """Build FileMetadata using the actual file by default."""
    stats = file_path.stat()

    return FileMetadata(
        name=name if name is not None else file_path.name,
        relative_path=(
            relative_path
            if relative_path is not None
            else file_path.relative_to(repository_root).as_posix()
        ),
        extension=(
            extension
            if extension is not None
            else file_path.suffix.lower()
        ),
        language=language,
        size_bytes=(
            size_bytes
            if size_bytes is not None
            else stats.st_size
        ),
        modified_time=(
            modified_time
            if modified_time is not None
            else datetime.fromtimestamp(stats.st_mtime).isoformat()
        ),
    )


def make_metadata(repository, scan_result):
    """Create a valid metadata dictionary matching the scan."""
    records = []

    for file_path in scan_result.files:
        language = (
            "Markdown"
            if file_path.suffix.lower() == ".md"
            else "Python"
        )

        records.append(
            make_file_metadata(
                file_path,
                repository.root,
                language=language,
            )
        )

    language_counts = {}

    for record in records:
        language_counts[record.language] = (
            language_counts.get(record.language, 0) + 1
        )

    return {
        "repository_name": repository.name,
        "repository_path": str(repository.root),
        "total_files": len(scan_result.files),
        "total_directories": len(scan_result.directories),
        "total_symlinks": len(scan_result.symlinks),
        "total_size_bytes": sum(
            record.size_bytes for record in records
        ),
        "languages": dict(sorted(language_counts.items())),
        "files": records,
    }


def find_issue(result, code):
    """Return the first issue with the specified code."""
    return next(
        (
            issue
            for issue in result.issues
            if issue.code == code
        ),
        None,
    )


# ---------------------------------------------------------------------------
# Successful validation
# ---------------------------------------------------------------------------

def test_valid_repository_metadata_is_accepted(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert result.is_valid is True
    assert result.healthy is True
    assert result.error_count == 0
    assert result.issues == ()


def test_repository_root_is_preserved(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert result.repository_root == repository.root


def test_file_validation_count_is_correct(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert result.files_validated == 3


def test_directory_validation_count_is_correct(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert result.directories_validated == 1


def test_symlink_validation_count_is_correct(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert result.symlinks_validated == 0


def test_total_validated_count_is_correct(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert result.total_validated == 4


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_invalid_repository_type_is_rejected(service):
    with pytest.raises(RepositoryMetadataValidationError):
        service.validate(
            object(),
            object(),
            {},
        )


def test_invalid_scan_result_type_is_rejected(
    service,
    repository,
):
    with pytest.raises(RepositoryMetadataValidationError):
        service.validate(
            repository,
            object(),
            {},
        )


def test_metadata_must_be_dictionary(
    service,
    repository,
    scan_result,
):
    with pytest.raises(RepositoryMetadataValidationError):
        service.validate(
            repository,
            scan_result,
            [],
        )


def test_scan_files_must_be_tuple(
    service,
    repository,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=[repository.root / "README.md"],
        directories=(),
        symlinks=(),
    )

    with pytest.raises(RepositoryMetadataValidationError):
        service.validate(
            repository,
            scan,
            {},
        )


def test_scan_directories_must_be_tuple(
    service,
    repository,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=(),
        directories=[repository.root / "app"],
        symlinks=(),
    )

    with pytest.raises(RepositoryMetadataValidationError):
        service.validate(
            repository,
            scan,
            {},
        )


def test_scan_symlinks_must_be_tuple(
    service,
    repository,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=(),
        directories=(),
        symlinks=[repository.root / "link"],
    )

    with pytest.raises(RepositoryMetadataValidationError):
        service.validate(
            repository,
            scan,
            {},
        )


def test_scan_entries_must_be_paths(
    service,
    repository,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=("README.md",),
        directories=(),
        symlinks=(),
    )

    with pytest.raises(RepositoryMetadataValidationError):
        service.validate(
            repository,
            scan,
            {},
        )


def test_repository_root_must_match_scan_root(
    service,
    repository,
    tmp_path,
):
    another_root = tmp_path / "another"
    another_root.mkdir()

    scan = RepositoryScanResult(
        root=another_root,
        files=(),
        directories=(),
        symlinks=(),
    )

    with pytest.raises(
        RepositoryMetadataValidationError,
        match="does not match",
    ):
        service.validate(
            repository,
            scan,
            {},
        )


# ---------------------------------------------------------------------------
# Required metadata fields
# ---------------------------------------------------------------------------

def test_missing_required_fields_are_reported(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        {},
    )

    assert result.is_valid is False
    assert result.error_count == 8

    assert all(
        issue.code == "METADATA_FIELD_MISSING"
        for issue in result.issues
    )


def test_missing_repository_name_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    del metadata["repository_name"]

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "METADATA_FIELD_MISSING") is not None


def test_missing_file_collection_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    del metadata["files"]

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "METADATA_FIELD_MISSING") is not None


def test_empty_repository_name_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["repository_name"] = ""

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "METADATA_FIELD_INVALID") is not None


def test_invalid_repository_path_type_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["repository_path"] = 123

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "METADATA_FIELD_INVALID") is not None


def test_negative_total_file_count_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["total_files"] = -1

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "METADATA_FIELD_INVALID") is not None


def test_boolean_total_file_count_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["total_files"] = True

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "METADATA_FIELD_INVALID") is not None


def test_invalid_language_container_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["languages"] = []

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "LANGUAGE_METADATA_INVALID") is not None


def test_invalid_file_metadata_container_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["files"] = ()

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "FILE_METADATA_COLLECTION_INVALID",
    ) is not None


# ---------------------------------------------------------------------------
# Repository identity validation
# ---------------------------------------------------------------------------

def test_repository_name_mismatch_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["repository_name"] = "different-name"

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "REPOSITORY_NAME_MISMATCH") is not None


def test_repository_path_mismatch_is_reported(
    service,
    repository,
    scan_result,
    tmp_path,
):
    metadata = make_metadata(repository, scan_result)
    metadata["repository_path"] = str(tmp_path / "another")

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "REPOSITORY_PATH_MISMATCH") is not None


# ---------------------------------------------------------------------------
# Aggregate count validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("total_files", "REPOSITORY_COUNT_MISMATCH"),
        ("total_directories", "REPOSITORY_COUNT_MISMATCH"),
        ("total_symlinks", "REPOSITORY_COUNT_MISMATCH"),
    ],
)
def test_repository_count_mismatch_is_reported(
    service,
    repository,
    scan_result,
    field,
    code,
):
    metadata = make_metadata(repository, scan_result)
    metadata[field] += 1

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, code) is not None


# ---------------------------------------------------------------------------
# File metadata validation
# ---------------------------------------------------------------------------

def test_file_metadata_record_must_be_file_metadata(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["files"][0] = {"name": "README.md"}

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "FILE_METADATA_RECORD_INVALID",
    ) is not None


def test_duplicate_file_metadata_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["files"].append(metadata["files"][0])

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "DUPLICATE_FILE_METADATA",
    ) is not None


def test_missing_file_metadata_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["files"].pop()

    metadata["total_files"] -= 1
    metadata["total_size_bytes"] = sum(
        record.size_bytes for record in metadata["files"]
    )

    from collections import Counter

    metadata["languages"] = dict(
        sorted(
            Counter(
                record.language for record in metadata["files"]
            ).items()
        )
    )

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "FILE_METADATA_MISSING") is not None


def test_file_metadata_for_unknown_file_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)

    unknown = repository.root / "unknown.py"
    unknown.write_text("print('unknown')", encoding="utf-8")

    metadata["files"].append(
        make_file_metadata(
            unknown,
            repository.root,
        )
    )

    metadata["total_files"] += 1
    metadata["total_size_bytes"] = sum(
        record.size_bytes for record in metadata["files"]
    )

    metadata["languages"] = {
        "Markdown": 1,
        "Python": 3,
    }

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "FILE_METADATA_NOT_IN_SCAN") is not None


def test_file_metadata_name_mismatch_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    original = metadata["files"][0]

    metadata["files"][0] = FileMetadata(
        name="wrong-name.md",
        relative_path=original.relative_path,
        extension=original.extension,
        language=original.language,
        size_bytes=original.size_bytes,
        modified_time=original.modified_time,
    )

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "FILE_METADATA_NAME_MISMATCH",
    ) is not None


def test_file_metadata_extension_mismatch_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    original = metadata["files"][0]

    metadata["files"][0] = FileMetadata(
        name=original.name,
        relative_path=original.relative_path,
        extension=".txt",
        language=original.language,
        size_bytes=original.size_bytes,
        modified_time=original.modified_time,
    )

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "FILE_METADATA_EXTENSION_MISMATCH",
    ) is not None


def test_file_metadata_size_mismatch_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    original = metadata["files"][0]

    metadata["files"][0] = FileMetadata(
        name=original.name,
        relative_path=original.relative_path,
        extension=original.extension,
        language=original.language,
        size_bytes=original.size_bytes + 100,
        modified_time=original.modified_time,
    )

    metadata["total_size_bytes"] = sum(
        record.size_bytes for record in metadata["files"]
    )

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "FILE_METADATA_SIZE_MISMATCH",
    ) is not None


def test_invalid_file_relative_path_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    original = metadata["files"][0]

    metadata["files"][0] = FileMetadata(
        name=original.name,
        relative_path="../outside.md",
        extension=original.extension,
        language=original.language,
        size_bytes=original.size_bytes,
        modified_time=original.modified_time,
    )

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "FILE_METADATA_PATH_INVALID",
    ) is not None


def test_invalid_file_timestamp_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    original = metadata["files"][0]

    metadata["files"][0] = FileMetadata(
        name=original.name,
        relative_path=original.relative_path,
        extension=original.extension,
        language=original.language,
        size_bytes=original.size_bytes,
        modified_time="not-a-timestamp",
    )

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "FILE_METADATA_TIME_INVALID",
    ) is not None


# ---------------------------------------------------------------------------
# Total size and language statistics
# ---------------------------------------------------------------------------

def test_total_size_mismatch_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["total_size_bytes"] += 10

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(result, "TOTAL_SIZE_MISMATCH") is not None


def test_language_statistics_mismatch_is_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["languages"] = {
        "Python": 3,
    }

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "LANGUAGE_STATISTICS_MISMATCH",
    ) is not None


def test_invalid_language_statistics_are_reported(
    service,
    repository,
    scan_result,
):
    metadata = make_metadata(repository, scan_result)
    metadata["languages"] = {
        "Python": -1,
    }

    result = service.validate(
        repository,
        scan_result,
        metadata,
    )

    assert find_issue(
        result,
        "LANGUAGE_STATISTICS_INVALID",
    ) is not None


# ---------------------------------------------------------------------------
# Empty repository validation
# ---------------------------------------------------------------------------

def test_empty_repository_metadata_is_valid(
    service,
    tmp_path,
):
    repository = RepositoryInfo(
        root=tmp_path,
        name=tmp_path.name,
        is_git_repository=False,
    )

    scan = RepositoryScanResult(
        root=tmp_path,
        files=(),
        directories=(),
        symlinks=(),
    )

    metadata = {
        "repository_name": repository.name,
        "repository_path": str(repository.root),
        "total_files": 0,
        "total_directories": 0,
        "total_symlinks": 0,
        "total_size_bytes": 0,
        "languages": {},
        "files": [],
    }

    result = service.validate(
        repository,
        scan,
        metadata,
    )

    assert result.is_valid is True
    assert result.total_validated == 0
    assert result.issues == ()


# ---------------------------------------------------------------------------
# Result and issue model validation
# ---------------------------------------------------------------------------

def test_metadata_issue_rejects_empty_code():
    with pytest.raises(RepositoryMetadataValidationError):
        RepositoryMetadataIssue(
            code="",
            message="Test issue",
        )


def test_metadata_issue_rejects_empty_message():
    with pytest.raises(RepositoryMetadataValidationError):
        RepositoryMetadataIssue(
            code="TEST",
            message="",
        )


def test_metadata_issue_rejects_non_string_path():
    with pytest.raises(RepositoryMetadataValidationError):
        RepositoryMetadataIssue(
            code="TEST",
            message="Test issue",
            path=123,
        )


def test_metadata_issue_is_immutable():
    issue = RepositoryMetadataIssue(
        code="TEST",
        message="Test issue",
    )

    with pytest.raises(FrozenInstanceError):
        issue.code = "CHANGED"


def test_validation_result_is_immutable(
    repository,
):
    result = RepositoryMetadataValidationResult(
        repository_root=repository.root,
        is_valid=True,
        files_validated=0,
        directories_validated=0,
        symlinks_validated=0,
        issues=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.is_valid = False


def test_validation_result_rejects_negative_counts(
    repository,
):
    with pytest.raises(RepositoryMetadataValidationError):
        RepositoryMetadataValidationResult(
            repository_root=repository.root,
            is_valid=True,
            files_validated=-1,
            directories_validated=0,
            symlinks_validated=0,
            issues=(),
        )


def test_validation_result_rejects_inconsistent_validity(
    repository,
):
    issue = RepositoryMetadataIssue(
        code="TEST",
        message="Test issue",
    )

    with pytest.raises(RepositoryMetadataValidationError):
        RepositoryMetadataValidationResult(
            repository_root=repository.root,
            is_valid=True,
            files_validated=0,
            directories_validated=0,
            symlinks_validated=0,
            issues=(issue,),
        )


def test_validation_result_rejects_non_tuple_issues(
    repository,
):
    with pytest.raises(RepositoryMetadataValidationError):
        RepositoryMetadataValidationResult(
            repository_root=repository.root,
            is_valid=True,
            files_validated=0,
            directories_validated=0,
            symlinks_validated=0,
            issues=[],
        )


def test_validation_result_healthy_property(
    repository,
):
    result = RepositoryMetadataValidationResult(
        repository_root=repository.root,
        is_valid=True,
        files_validated=2,
        directories_validated=1,
        symlinks_validated=0,
        issues=(),
    )

    assert result.healthy is True
    assert result.error_count == 0
    assert result.total_validated == 3
