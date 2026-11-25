
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.application.file_directory_integrity_service import (
    FileDirectoryIntegrityError,
    FileDirectoryIntegrityIssue,
    FileDirectoryIntegrityResult,
    FileDirectoryIntegrityService,
    IntegritySeverity,
)
from app.application.repository_input import RepositoryInfo
from app.application.repository_scanner import RepositoryScanResult


# ---------------------------------------------------------------------------
# Fixtures and helper functions
# ---------------------------------------------------------------------------

@pytest.fixture
def repository(tmp_path):
    """Create a sample repository with files and directories."""
    (tmp_path / "README.md").write_text(
        "# Test Repository",
        encoding="utf-8",
    )

    app_directory = tmp_path / "app"
    app_directory.mkdir()

    (app_directory / "main.py").write_text(
        "print('Hello World')",
        encoding="utf-8",
    )

    return RepositoryInfo(
        root=tmp_path,
        name=tmp_path.name,
        is_git_repository=False,
    )


@pytest.fixture
def service():
    """Return a FileDirectoryIntegrityService instance."""
    return FileDirectoryIntegrityService()


def make_scan_result(
    root,
    files=(),
    directories=(),
    symlinks=(),
):
    """Create a repository scan result for testing."""
    return RepositoryScanResult(
        root=root,
        files=tuple(files),
        directories=tuple(directories),
        symlinks=tuple(symlinks),
    )


def find_issue(result, code):
    """Find an issue by its error code."""
    return next(
        (issue for issue in result.issues if issue.code == code),
        None,
    )


def create_symlink_or_skip(link_path, target_path, target_is_directory=False):
    """Create a symbolic link or skip when the OS does not support it."""
    try:
        link_path.symlink_to(
            target_path,
            target_is_directory=target_is_directory,
        )
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic link creation is not supported.")


# ---------------------------------------------------------------------------
# Basic validation
# ---------------------------------------------------------------------------

def test_valid_repository_has_no_integrity_issues(
    service,
    repository,
):
    scan = make_scan_result(
        repository.root,
        files=(
            repository.root / "README.md",
            repository.root / "app" / "main.py",
        ),
        directories=(
            repository.root / "app",
        ),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is True
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.issues == ()


def test_repository_root_is_preserved(
    service,
    repository,
):
    scan = make_scan_result(repository.root)

    result = service.validate(repository, scan)

    assert result.repository_root == repository.root


def test_all_discovered_files_are_checked(
    service,
    repository,
):
    scan = make_scan_result(
        repository.root,
        files=(
            repository.root / "README.md",
            repository.root / "app" / "main.py",
        ),
    )

    result = service.validate(repository, scan)

    assert result.files_checked == 2


def test_all_discovered_directories_are_checked(
    service,
    repository,
):
    scan = make_scan_result(
        repository.root,
        directories=(
            repository.root / "app",
        ),
    )

    result = service.validate(repository, scan)

    assert result.directories_checked == 1


def test_all_discovered_symlinks_are_checked(
    service,
    repository,
):
    scan = make_scan_result(
        repository.root,
        symlinks=(
            repository.root / "link-one",
            repository.root / "link-two",
        ),
    )

    result = service.validate(repository, scan)

    assert result.symlinks_checked == 2


def test_total_checked_matches_all_entry_types(
    service,
    repository,
):
    scan = make_scan_result(
        repository.root,
        files=(repository.root / "README.md",),
        directories=(repository.root / "app",),
        symlinks=(repository.root / "missing-link",),
    )

    result = service.validate(repository, scan)

    assert result.total_checked == 3


# ---------------------------------------------------------------------------
# Valid files and directories
# ---------------------------------------------------------------------------

def test_valid_file_is_accepted(
    service,
    repository,
):
    file_path = repository.root / "README.md"

    scan = make_scan_result(
        repository.root,
        files=(file_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is True
    assert result.issues == ()


def test_valid_directory_is_accepted(
    service,
    repository,
):
    directory_path = repository.root / "app"

    scan = make_scan_result(
        repository.root,
        directories=(directory_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is True
    assert result.issues == ()


# ---------------------------------------------------------------------------
# Missing files and directories
# ---------------------------------------------------------------------------

def test_missing_file_is_reported(
    service,
    repository,
):
    missing_file = repository.root / "missing.py"

    scan = make_scan_result(
        repository.root,
        files=(missing_file,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert result.error_count == 1

    issue = result.issues[0]

    assert issue.code == "FILE_MISSING"
    assert issue.path == missing_file
    assert isinstance(issue.path, Path)
    assert issue.entry_type == "file"


def test_missing_directory_is_reported(
    service,
    repository,
):
    missing_directory = repository.root / "missing_directory"

    scan = make_scan_result(
        repository.root,
        directories=(missing_directory,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert result.error_count == 1

    issue = result.issues[0]

    assert issue.code == "DIRECTORY_MISSING"
    assert issue.path == missing_directory
    assert isinstance(issue.path, Path)
    assert issue.entry_type == "directory"


# ---------------------------------------------------------------------------
# File and directory type validation
# ---------------------------------------------------------------------------

def test_file_that_becomes_directory_is_reported(
    service,
    repository,
):
    directory_path = repository.root / "app"

    scan = make_scan_result(
        repository.root,
        files=(directory_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert find_issue(result, "FILE_TYPE_INVALID") is not None


def test_directory_that_becomes_file_is_reported(
    service,
    repository,
):
    file_path = repository.root / "README.md"

    scan = make_scan_result(
        repository.root,
        directories=(file_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert find_issue(result, "DIRECTORY_TYPE_INVALID") is not None


# ---------------------------------------------------------------------------
# File and directory accessibility
# ---------------------------------------------------------------------------

def test_file_not_readable_is_reported(
    service,
    repository,
    monkeypatch,
):
    file_path = repository.root / "README.md"

    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: False,
    )

    scan = make_scan_result(
        repository.root,
        files=(file_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert find_issue(result, "FILE_NOT_READABLE") is not None


def test_directory_not_accessible_is_reported(
    service,
    repository,
    monkeypatch,
):
    directory_path = repository.root / "app"

    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: False,
    )

    scan = make_scan_result(
        repository.root,
        directories=(directory_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False

    issue = find_issue(
        result,
        "DIRECTORY_NOT_ACCESSIBLE",
    )

    assert issue is not None


# ---------------------------------------------------------------------------
# Repository boundary validation
# ---------------------------------------------------------------------------

def test_file_outside_repository_is_reported(
    service,
    repository,
    tmp_path,
):
    outside_file = tmp_path.parent / "outside.py"

    scan = make_scan_result(
        repository.root,
        files=(outside_file,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert find_issue(
        result,
        "ENTRY_OUTSIDE_REPOSITORY",
    ) is not None


def test_directory_outside_repository_is_reported(
    service,
    repository,
    tmp_path,
):
    outside_directory = tmp_path.parent / "outside_directory"

    scan = make_scan_result(
        repository.root,
        directories=(outside_directory,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert find_issue(
        result,
        "ENTRY_OUTSIDE_REPOSITORY",
    ) is not None


def test_repository_root_cannot_be_a_discovered_file(
    service,
    repository,
):
    scan = make_scan_result(
        repository.root,
        files=(repository.root,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert find_issue(
        result,
        "INVALID_ROOT_ENTRY",
    ) is not None


def test_repository_root_cannot_be_a_discovered_directory(
    service,
    repository,
):
    scan = make_scan_result(
        repository.root,
        directories=(repository.root,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False
    assert find_issue(
        result,
        "INVALID_ROOT_ENTRY",
    ) is not None


# ---------------------------------------------------------------------------
# Repository and scan input validation
# ---------------------------------------------------------------------------

def test_scan_root_mismatch_is_rejected(
    service,
    repository,
    tmp_path,
):
    another_root = tmp_path / "another_repository"
    another_root.mkdir()

    scan = make_scan_result(another_root)

    with pytest.raises(
        FileDirectoryIntegrityError,
        match="does not match",
    ):
        service.validate(repository, scan)


def test_invalid_repository_type_is_rejected(
    service,
):
    scan = make_scan_result(Path.cwd())

    with pytest.raises(FileDirectoryIntegrityError):
        service.validate(object(), scan)


def test_invalid_scan_result_type_is_rejected(
    service,
    repository,
):
    with pytest.raises(FileDirectoryIntegrityError):
        service.validate(repository, object())


def test_scan_result_files_must_be_tuple(
    service,
    repository,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=[repository.root / "README.md"],
        directories=(),
        symlinks=(),
    )

    with pytest.raises(FileDirectoryIntegrityError):
        service.validate(repository, scan)


def test_scan_result_directories_must_be_tuple(
    service,
    repository,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=(),
        directories=[repository.root / "app"],
        symlinks=(),
    )

    with pytest.raises(FileDirectoryIntegrityError):
        service.validate(repository, scan)


def test_scan_result_entries_must_be_paths(
    service,
    repository,
):
    scan = RepositoryScanResult(
        root=repository.root,
        files=("README.md",),
        directories=(),
        symlinks=(),
    )

    with pytest.raises(FileDirectoryIntegrityError):
        service.validate(repository, scan)



# ---------------------------------------------------------------------------
# Empty repository scan
# ---------------------------------------------------------------------------

def test_empty_repository_scan_is_valid(
    service,
    repository,
):
    scan = make_scan_result(repository.root)

    result = service.validate(repository, scan)

    assert result.is_valid is True
    assert result.total_checked == 0
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.issues == ()


# ---------------------------------------------------------------------------
# Integrity issue model validation
# ---------------------------------------------------------------------------

def test_integrity_issue_rejects_empty_code(
    repository,
):
    with pytest.raises(FileDirectoryIntegrityError):
        FileDirectoryIntegrityIssue(
            code="",
            message="Test message",
            path=repository.root / "file.py",
            entry_type="file",
        )


def test_integrity_issue_rejects_empty_message(
    repository,
):
    with pytest.raises(FileDirectoryIntegrityError):
        FileDirectoryIntegrityIssue(
            code="TEST_ERROR",
            message="",
            path=repository.root / "file.py",
            entry_type="file",
        )


def test_integrity_issue_rejects_invalid_entry_type(
    repository,
):
    with pytest.raises(FileDirectoryIntegrityError):
        FileDirectoryIntegrityIssue(
            code="TEST_ERROR",
            message="Test message",
            path=repository.root / "file.py",
            entry_type="invalid",
        )


def test_integrity_issue_rejects_invalid_severity(
    repository,
):
    with pytest.raises(FileDirectoryIntegrityError):
        FileDirectoryIntegrityIssue(
            code="TEST_ERROR",
            message="Test message",
            path=repository.root / "file.py",
            entry_type="file",
            severity="error",
        )


def test_integrity_issue_rejects_string_path(
    repository,
):
    with pytest.raises(FileDirectoryIntegrityError):
        FileDirectoryIntegrityIssue(
            code="TEST_ERROR",
            message="Test message",
            path=str(repository.root / "file.py"),
            entry_type="file",
        )


def test_integrity_severity_values():
    assert IntegritySeverity.ERROR.value == "error"
    assert IntegritySeverity.WARNING.value == "warning"


# ---------------------------------------------------------------------------
# Result model validation and properties
# ---------------------------------------------------------------------------

def test_result_error_and_warning_counts(
    repository,
):
    issues = (
        FileDirectoryIntegrityIssue(
            code="ERROR_ONE",
            message="First error",
            path=repository.root / "one.py",
            entry_type="file",
            severity=IntegritySeverity.ERROR,
        ),
        FileDirectoryIntegrityIssue(
            code="WARNING_ONE",
            message="First warning",
            path=repository.root / "two.py",
            entry_type="file",
            severity=IntegritySeverity.WARNING,
        ),
        FileDirectoryIntegrityIssue(
            code="ERROR_TWO",
            message="Second error",
            path=repository.root / "three.py",
            entry_type="file",
            severity=IntegritySeverity.ERROR,
        ),
    )

    result = FileDirectoryIntegrityResult(
        repository_root=repository.root,
        is_valid=False,
        files_checked=3,
        directories_checked=0,
        symlinks_checked=0,
        issues=issues,
    )

    assert result.error_count == 2
    assert result.warning_count == 1
    assert result.total_checked == 3
    assert result.healthy is False


def test_result_is_immutable(
    repository,
):
    result = FileDirectoryIntegrityResult(
        repository_root=repository.root,
        is_valid=True,
        files_checked=0,
        directories_checked=0,
        symlinks_checked=0,
        issues=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.is_valid = False


def test_issue_is_immutable(
    repository,
):
    issue = FileDirectoryIntegrityIssue(
        code="TEST_ERROR",
        message="Test message",
        path=repository.root / "file.py",
        entry_type="file",
    )

    with pytest.raises(FrozenInstanceError):
        issue.code = "CHANGED"


# ---------------------------------------------------------------------------
# Filesystem metadata permission handling
# ---------------------------------------------------------------------------

def test_file_metadata_access_error_is_reported(
    service,
    repository,
    monkeypatch,
):
    file_path = repository.root / "README.md"
    original_stat = Path.stat

    def fake_stat(path, *args, **kwargs):
        if path == file_path:
            raise PermissionError("Access denied")

        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    scan = make_scan_result(
        repository.root,
        files=(file_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False

    issue = find_issue(
        result,
        "FILE_METADATA_ACCESS_DENIED",
    )

    assert issue is not None
    assert issue.path == file_path


def test_directory_metadata_access_error_is_reported(
    service,
    repository,
    monkeypatch,
):
    directory_path = repository.root / "app"
    original_stat = Path.stat

    def fake_stat(path, *args, **kwargs):
        if path == directory_path:
            raise PermissionError("Access denied")

        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    scan = make_scan_result(
        repository.root,
        directories=(directory_path,),
    )

    result = service.validate(repository, scan)

    assert result.is_valid is False

    issue = find_issue(
        result,
        "DIRECTORY_METADATA_ACCESS_DENIED",
    )

    assert issue is not None
    assert issue.path == directory_path
