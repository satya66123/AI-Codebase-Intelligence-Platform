
from pathlib import Path

import pytest

from appy.application.repository_input import validate_repository_path
from appy.application.repository_scanner import (
    RepositoryScanResult,
    RepositoryScanner,
)
from appy.application.repository_structure_validation_service import (
    RepositoryStructureIssue,
    RepositoryStructureValidationError,
    RepositoryStructureValidationResult,
    RepositoryStructureValidationService,
    StructureIssueSeverity,
)


@pytest.fixture
def service():
    return RepositoryStructureValidationService()


@pytest.fixture
def repository(tmp_path):
    (tmp_path / "appy").mkdir()
    (tmp_path / "tests").mkdir()

    (tmp_path / "README.md").write_text(
        "# Test Repository",
        encoding="utf-8",
    )

    (tmp_path / "appy" / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    (tmp_path / "tests" / "test_main.py").write_text(
        "def test_example(): pass",
        encoding="utf-8",
    )

    return validate_repository_path(str(tmp_path))


@pytest.fixture
def scan_result(repository):
    return RepositoryScanner().scan(repository)


def make_scan_result(
    root,
    files=(),
    directories=(),
    symlinks=(),
):
    return RepositoryScanResult(
        root=root,
        files=tuple(files),
        directories=tuple(directories),
        symlinks=tuple(symlinks),
    )


def test_valid_repository_structure(service, repository, scan_result):
    result = service.validate(repository, scan_result)

    assert isinstance(result, RepositoryStructureValidationResult)
    assert result.is_valid is True
    assert result.error_count == 0
    assert result.total_files == 3
    assert result.total_directories == 2


def test_repository_root_is_preserved(service, repository, scan_result):
    result = service.validate(repository, scan_result)

    assert result.repository_root == repository.root


def test_required_files_exist(service, repository, scan_result):
    result = service.validate(
        repository,
        scan_result,
        required_files=("README.md", "appy/main.py"),
    )

    assert result.is_valid is True
    assert result.missing_count == 0


def test_required_directories_exist(service, repository, scan_result):
    result = service.validate(
        repository,
        scan_result,
        required_directories=("appy", "tests"),
    )

    assert result.is_valid is True
    assert result.missing_count == 0


def test_missing_required_file_is_reported(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_files=("requirements.txt",),
    )

    assert result.is_valid is False
    assert result.missing_count == 1
    assert result.issues[0].code == "MISSING_REQUIRED_FILE"
    assert result.issues[0].path == "requirements.txt"


def test_missing_required_directory_is_reported(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_directories=("src",),
    )

    assert result.is_valid is False
    assert result.missing_count == 1
    assert result.issues[0].code == "MISSING_REQUIRED_DIRECTORY"
    assert result.issues[0].path == "src"


def test_required_file_must_be_a_file(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_files=("appy",),
    )

    assert result.is_valid is False
    assert any(
        issue.code == "REQUIRED_PATH_TYPE_MISMATCH"
        for issue in result.issues
    )


def test_required_directory_must_be_a_directory(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_directories=("README.md",),
    )

    assert result.is_valid is False
    assert any(
        issue.code == "REQUIRED_PATH_TYPE_MISMATCH"
        for issue in result.issues
    )


def test_multiple_missing_paths_are_reported(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_files=("missing1.py", "missing2.py"),
        required_directories=("missing_dir",),
    )

    assert result.is_valid is False
    assert result.missing_count == 3


def test_duplicate_required_paths_are_checked_once(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_files=("missing.py", "missing.py"),
    )

    assert result.missing_count == 1


def test_scan_root_mismatch_is_reported(
    service,
    repository,
    scan_result,
    tmp_path,
):
    other_root = tmp_path / "other"
    other_root.mkdir()

    mismatched_result = make_scan_result(
        root=other_root,
        files=scan_result.files,
        directories=scan_result.directories,
        symlinks=scan_result.symlinks,
    )

    result = service.validate(repository, mismatched_result)

    assert result.is_valid is False
    assert any(
        issue.code == "SCAN_ROOT_MISMATCH"
        for issue in result.issues
    )


def test_entry_outside_repository_is_reported(
    service,
    repository,
    scan_result,
    tmp_path,
):
    outside_file = tmp_path.parent / "outside.py"
    outside_file.write_text(
        "print('outside')",
        encoding="utf-8",
    )

    invalid_result = make_scan_result(
        root=repository.root,
        files=scan_result.files + (outside_file,),
        directories=scan_result.directories,
        symlinks=scan_result.symlinks,
    )

    result = service.validate(repository, invalid_result)

    assert result.is_valid is False
    assert any(
        issue.code == "ENTRY_OUTSIDE_REPOSITORY"
        for issue in result.issues
    )


def test_duplicate_scan_entries_are_reported(
    service,
    repository,
    scan_result,
):
    duplicate_file = scan_result.files[0]

    invalid_result = make_scan_result(
        root=repository.root,
        files=scan_result.files + (duplicate_file,),
        directories=scan_result.directories,
        symlinks=scan_result.symlinks,
    )

    result = service.validate(repository, invalid_result)

    assert result.is_valid is False
    assert any(
        issue.code == "DUPLICATE_ENTRY"
        for issue in result.issues
    )


def test_file_entry_with_directory_path_is_reported(
    service,
    repository,
    scan_result,
):
    directory = scan_result.directories[0]

    invalid_result = make_scan_result(
        root=repository.root,
        files=(directory,),
    )

    result = service.validate(repository, invalid_result)

    assert result.is_valid is False
    assert any(
        issue.code == "ENTRY_TYPE_MISMATCH"
        for issue in result.issues
    )


def test_discovered_entry_that_no_longer_exists_is_reported(
    service,
    repository,
    scan_result,
):
    missing_file = repository.root / "deleted.py"

    invalid_result = make_scan_result(
        root=repository.root,
        files=scan_result.files + (missing_file,),
        directories=scan_result.directories,
        symlinks=scan_result.symlinks,
    )

    result = service.validate(repository, invalid_result)

    assert result.is_valid is False
    assert any(
        issue.code == "DISCOVERED_ENTRY_MISSING"
        for issue in result.issues
    )


def test_cross_category_entry_conflict_is_reported(
    service,
    repository,
    scan_result,
):
    shared_path = scan_result.files[0]

    invalid_result = make_scan_result(
        root=repository.root,
        files=(shared_path,),
        directories=(shared_path,),
    )

    result = service.validate(repository, invalid_result)

    assert result.is_valid is False
    assert any(
        issue.code == "ENTRY_CATEGORY_CONFLICT"
        for issue in result.issues
    )


def test_invalid_repository_input_is_rejected(
    service,
    scan_result,
):
    with pytest.raises(
        RepositoryStructureValidationError,
        match="RepositoryInfo",
    ):
        service.validate(object(), scan_result)


def test_invalid_scan_result_input_is_rejected(
    service,
    repository,
):
    with pytest.raises(
        RepositoryStructureValidationError,
        match="RepositoryScanResult",
    ):
        service.validate(repository, object())


def test_scan_result_entries_must_be_tuples(
    service,
    repository,
    scan_result,
):
    invalid_result = RepositoryScanResult(
        root=repository.root,
        files=list(scan_result.files),
        directories=scan_result.directories,
        symlinks=scan_result.symlinks,
    )

    with pytest.raises(
        RepositoryStructureValidationError,
        match="must be a tuple",
    ):
        service.validate(repository, invalid_result)


@pytest.mark.parametrize(
    "required_path",
    [
        "../outside.py",
        "..\\outside.py",
        "/absolute/path.py",
        "\\absolute\\path.py",
        "C:\\absolute\\path.py",
        "C:/absolute/path.py",
        "C:relative_path.py",
        "",
        ".",
    ],
)
def test_invalid_required_file_paths_are_rejected(
    service,
    repository,
    scan_result,
    required_path,
):
    with pytest.raises(RepositoryStructureValidationError):
        service.validate(
            repository,
            scan_result,
            required_files=(required_path,),
        )


def test_required_paths_must_be_iterable(
    service,
    repository,
    scan_result,
):
    with pytest.raises(RepositoryStructureValidationError):
        service.validate(
            repository,
            scan_result,
            required_files=None,
        )


def test_required_paths_cannot_be_a_single_string(
    service,
    repository,
    scan_result,
):
    with pytest.raises(RepositoryStructureValidationError):
        service.validate(
            repository,
            scan_result,
            required_files="README.md",
        )


def test_required_paths_cannot_be_a_single_path_object(
    service,
    repository,
    scan_result,
):
    with pytest.raises(RepositoryStructureValidationError):
        service.validate(
            repository,
            scan_result,
            required_files=Path("README.md"),
        )


def test_issue_model_rejects_empty_code():
    with pytest.raises(RepositoryStructureValidationError):
        RepositoryStructureIssue(
            code="",
            message="Test message",
        )


def test_issue_model_rejects_empty_message():
    with pytest.raises(RepositoryStructureValidationError):
        RepositoryStructureIssue(
            code="TEST",
            message="",
        )


def test_issue_model_rejects_invalid_severity():
    with pytest.raises(RepositoryStructureValidationError):
        RepositoryStructureIssue(
            code="TEST",
            message="Test message",
            severity="invalid",
        )


def test_issue_severity_values():
    assert StructureIssueSeverity.ERROR.value == "error"
    assert StructureIssueSeverity.WARNING.value == "warning"


def test_valid_repository_has_no_warnings(
    service,
    repository,
    scan_result,
):
    result = service.validate(repository, scan_result)

    assert result.warning_count == 0


def test_result_counts_match_scan_result(
    service,
    repository,
    scan_result,
):
    result = service.validate(repository, scan_result)

    assert result.total_files == scan_result.total_files
    assert result.total_directories == scan_result.total_directories
    assert result.total_symlinks == scan_result.total_symlinks


def test_empty_required_paths_are_allowed(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_files=(),
        required_directories=(),
    )

    assert result.is_valid is True


def test_required_paths_accept_path_objects(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_files=(Path("README.md"),),
        required_directories=(Path("appy"),),
    )

    assert result.is_valid is True


def test_required_paths_accept_generator(
    service,
    repository,
    scan_result,
):
    result = service.validate(
        repository,
        scan_result,
        required_files=(path for path in ("README.md", "appy/main.py")),
    )

    assert result.is_valid is True


def test_missing_count_does_not_count_other_issues():
    result = RepositoryStructureValidationResult(
        repository_root=Path("."),
        is_valid=False,
        total_files=0,
        total_directories=0,
        total_symlinks=0,
        issues=(
            RepositoryStructureIssue(
                code="ENTRY_OUTSIDE_REPOSITORY",
                message="Outside repository.",
            ),
            RepositoryStructureIssue(
                code="MISSING_REQUIRED_FILE",
                message="Required file missing.",
            ),
            RepositoryStructureIssue(
                code="MISSING_REQUIRED_DIRECTORY",
                message="Required directory missing.",
            ),
        ),
    )

    assert result.missing_count == 2
    assert result.error_count == 3
