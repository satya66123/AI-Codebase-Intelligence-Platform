
import os
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import RepositoryScanResult


class FileDirectoryIntegrityError(ValueError):
    """Raised when file and directory integrity validation cannot proceed."""


class IntegritySeverity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class FileDirectoryIntegrityIssue:
    """Represents one file, directory, or symbolic-link integrity issue."""

    code: str
    message: str
    path: Path
    entry_type: str
    severity: IntegritySeverity = IntegritySeverity.ERROR

    def __post_init__(self):
        if not isinstance(self.code, str) or not self.code.strip():
            raise FileDirectoryIntegrityError(
                "Issue code must be a non-empty string."
            )

        if not isinstance(self.message, str) or not self.message.strip():
            raise FileDirectoryIntegrityError(
                "Issue message must be a non-empty string."
            )

        if not isinstance(self.path, Path):
            raise FileDirectoryIntegrityError(
                "Issue path must be a Path."
            )

        if self.entry_type not in {"file", "directory", "symlink"}:
            raise FileDirectoryIntegrityError(
                "Entry type must be file, directory, or symlink."
            )

        if not isinstance(self.severity, IntegritySeverity):
            raise FileDirectoryIntegrityError(
                "Severity must be an IntegritySeverity value."
            )


@dataclass(frozen=True)
class FileDirectoryIntegrityResult:
    """Immutable result of repository file and directory validation."""

    repository_root: Path
    is_valid: bool
    files_checked: int
    directories_checked: int
    symlinks_checked: int
    issues: tuple[FileDirectoryIntegrityIssue, ...]

    def __post_init__(self):
        if not isinstance(self.repository_root, Path):
            raise FileDirectoryIntegrityError(
                "Repository root must be a Path."
            )

        if not isinstance(self.is_valid, bool):
            raise FileDirectoryIntegrityError(
                "is_valid must be a boolean."
            )

        for field_name in (
            "files_checked",
            "directories_checked",
            "symlinks_checked",
        ):
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, int):
                raise FileDirectoryIntegrityError(
                    f"{field_name} must be an integer."
                )

            if value < 0:
                raise FileDirectoryIntegrityError(
                    f"{field_name} cannot be negative."
                )

        if not isinstance(self.issues, tuple):
            raise FileDirectoryIntegrityError(
                "Issues must be provided as a tuple."
            )

        if not all(
            isinstance(issue, FileDirectoryIntegrityIssue)
            for issue in self.issues
        ):
            raise FileDirectoryIntegrityError(
                "Every issue must be a FileDirectoryIntegrityIssue."
            )

        has_errors = any(
            issue.severity == IntegritySeverity.ERROR
            for issue in self.issues
        )

        if self.is_valid == has_errors:
            raise FileDirectoryIntegrityError(
                "is_valid must be false when errors exist and true otherwise."
            )

    @property
    def total_checked(self) -> int:
        return (
            self.files_checked
            + self.directories_checked
            + self.symlinks_checked
        )

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity == IntegritySeverity.ERROR
            for issue in self.issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity == IntegritySeverity.WARNING
            for issue in self.issues
        )

    @property
    def healthy(self) -> bool:
        return self.error_count == 0


class FileDirectoryIntegrityService:
    """
    Validates discovered repository files, directories, and symbolic links.

    The service checks that discovered entries:
    - remain inside the repository root;
    - still exist;
    - retain their expected filesystem type;
    - can be accessed as required;
    - have readable file metadata;
    - have accessible directory metadata;
    - do not unexpectedly become symbolic links.

    Symbolic links are checked separately because their targets may be
    missing or inaccessible.
    """

    def validate(
        self,
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
    ) -> FileDirectoryIntegrityResult:
        """
        Validate all entries in a repository scan.

        Args:
            repository: Validated repository information.
            scan_result: Result returned by RepositoryScanner.

        Returns:
            FileDirectoryIntegrityResult containing validation counts
            and all detected issues.

        Raises:
            FileDirectoryIntegrityError: If the supplied inputs are invalid.
        """
        self._validate_inputs(repository, scan_result)

        repository_root = repository.root.resolve(strict=False)
        scan_root = scan_result.root.resolve(strict=False)

        if repository_root != scan_root:
            raise FileDirectoryIntegrityError(
                "Repository root does not match scan result root."
            )

        issues = []

        files_checked = len(scan_result.files)
        directories_checked = len(scan_result.directories)
        symlinks_checked = len(scan_result.symlinks)

        for path in scan_result.files:
            self._check_regular_file(
                repository_root=repository_root,
                path=path,
                issues=issues,
            )

        for path in scan_result.directories:
            self._check_directory(
                repository_root=repository_root,
                path=path,
                issues=issues,
            )

        for path in scan_result.symlinks:
            self._check_symlink(
                repository_root=repository_root,
                path=path,
                issues=issues,
            )

        issue_tuple = tuple(issues)
        has_errors = any(
            issue.severity == IntegritySeverity.ERROR
            for issue in issue_tuple
        )

        return FileDirectoryIntegrityResult(
            repository_root=repository.root,
            is_valid=not has_errors,
            files_checked=files_checked,
            directories_checked=directories_checked,
            symlinks_checked=symlinks_checked,
            issues=issue_tuple,
        )

    @staticmethod
    def _validate_inputs(
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
    ) -> None:
        """Validate the repository and scanner result structures."""
        if not isinstance(repository, RepositoryInfo):
            raise FileDirectoryIntegrityError(
                "repository must be a RepositoryInfo instance."
            )

        if not isinstance(scan_result, RepositoryScanResult):
            raise FileDirectoryIntegrityError(
                "scan_result must be a RepositoryScanResult instance."
            )

        if not isinstance(repository.root, Path):
            raise FileDirectoryIntegrityError(
                "Repository root must be a Path."
            )

        if not isinstance(scan_result.root, Path):
            raise FileDirectoryIntegrityError(
                "Scan root must be a Path."
            )

        for field_name in ("files", "directories", "symlinks"):
            entries = getattr(scan_result, field_name)

            if not isinstance(entries, tuple):
                raise FileDirectoryIntegrityError(
                    f"Scan result {field_name} must be a tuple."
                )

            if not all(isinstance(entry, Path) for entry in entries):
                raise FileDirectoryIntegrityError(
                    f"Every entry in {field_name} must be a Path."
                )

    @staticmethod
    def _add_issue(
        issues: list,
        code: str,
        message: str,
        path: Path,
        entry_type: str,
        severity: IntegritySeverity = IntegritySeverity.ERROR,
    ) -> None:
        """Append a consistently structured integrity issue."""
        issues.append(
            FileDirectoryIntegrityIssue(
                code=code,
                message=message,
                path=path,
                entry_type=entry_type,
                severity=severity,
            )
        )

    @staticmethod
    def _relative_path(
        repository_root: Path,
        path: Path,
        entry_type: str,
        issues: list,
    ) -> bool:
        """Check lexical containment without following the entry itself."""
        try:
            relative_path = path.relative_to(repository_root)
        except ValueError:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="ENTRY_OUTSIDE_REPOSITORY",
                message="Discovered entry is outside the repository root.",
                path=path,
                entry_type=entry_type,
            )
            return False

        if relative_path == Path("."):
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="INVALID_ROOT_ENTRY",
                message="Repository root cannot be a discovered entry.",
                path=path,
                entry_type=entry_type,
            )
            return False

        return True

    @staticmethod
    def _check_symlink_status(
        path: Path,
        entry_type: str,
        issues: list,
    ) -> bool | None:
        """
        Safely determine whether an entry is a symbolic link.

        Returns:
            True: The entry is a symbolic link.
            False: The entry is not a symbolic link.
            None: Its status could not be determined.
        """
        try:
            return path.is_symlink()

        except PermissionError as exc:
            code = (
                "FILE_METADATA_ACCESS_DENIED"
                if entry_type == "file"
                else "DIRECTORY_METADATA_ACCESS_DENIED"
            )

            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code=code,
                message=(
                    f"Permission denied while checking {entry_type} "
                    f"symbolic-link status: {exc}"
                ),
                path=path,
                entry_type=entry_type,
            )
            return None

        except OSError as exc:
            code = (
                "FILE_METADATA_READ_FAILED"
                if entry_type == "file"
                else "DIRECTORY_METADATA_READ_FAILED"
            )

            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code=code,
                message=(
                    f"Unable to inspect {entry_type} symbolic-link "
                    f"status: {exc}"
                ),
                path=path,
                entry_type=entry_type,
            )
            return None

    @staticmethod
    def _check_regular_file(
        repository_root: Path,
        path: Path,
        issues: list,
    ) -> None:
        """Validate a discovered regular file."""
        if not FileDirectoryIntegrityService._relative_path(
            repository_root,
            path,
            "file",
            issues,
        ):
            return

        symlink_status = (
            FileDirectoryIntegrityService._check_symlink_status(
                path,
                "file",
                issues,
            )
        )

        if symlink_status is None:
            return

        if symlink_status:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="FILE_BECAME_SYMLINK",
                message="Discovered file unexpectedly became a symbolic link.",
                path=path,
                entry_type="file",
            )
            return

        try:
            metadata = path.stat()

        except FileNotFoundError:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="FILE_MISSING",
                message="Discovered file no longer exists.",
                path=path,
                entry_type="file",
            )
            return

        except PermissionError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="FILE_METADATA_ACCESS_DENIED",
                message=f"Permission denied while reading file metadata: {exc}",
                path=path,
                entry_type="file",
            )
            return

        except OSError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="FILE_METADATA_READ_FAILED",
                message=f"Unable to read file metadata: {exc}",
                path=path,
                entry_type="file",
            )
            return

        if not stat.S_ISREG(metadata.st_mode):
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="FILE_TYPE_INVALID",
                message="Discovered file is no longer a regular file.",
                path=path,
                entry_type="file",
            )
            return

        try:
            readable = os.access(path, os.R_OK)

        except OSError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="FILE_NOT_READABLE",
                message=f"Unable to verify file readability: {exc}",
                path=path,
                entry_type="file",
            )
            return

        if not readable:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="FILE_NOT_READABLE",
                message="Discovered file is not readable.",
                path=path,
                entry_type="file",
            )

    @staticmethod
    def _check_directory(
        repository_root: Path,
        path: Path,
        issues: list,
    ) -> None:
        """Validate a discovered directory."""
        if not FileDirectoryIntegrityService._relative_path(
            repository_root,
            path,
            "directory",
            issues,
        ):
            return

        symlink_status = (
            FileDirectoryIntegrityService._check_symlink_status(
                path,
                "directory",
                issues,
            )
        )

        if symlink_status is None:
            return

        if symlink_status:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="DIRECTORY_BECAME_SYMLINK",
                message=(
                    "Discovered directory unexpectedly became "
                    "a symbolic link."
                ),
                path=path,
                entry_type="directory",
            )
            return

        try:
            metadata = path.stat()

        except FileNotFoundError:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="DIRECTORY_MISSING",
                message="Discovered directory no longer exists.",
                path=path,
                entry_type="directory",
            )
            return

        except PermissionError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="DIRECTORY_METADATA_ACCESS_DENIED",
                message=(
                    f"Permission denied while reading directory metadata: {exc}"
                ),
                path=path,
                entry_type="directory",
            )
            return

        except OSError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="DIRECTORY_METADATA_READ_FAILED",
                message=f"Unable to read directory metadata: {exc}",
                path=path,
                entry_type="directory",
            )
            return

        if not stat.S_ISDIR(metadata.st_mode):
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="DIRECTORY_TYPE_INVALID",
                message="Discovered directory is no longer a directory.",
                path=path,
                entry_type="directory",
            )
            return

        try:
            accessible = os.access(
                path,
                os.R_OK | os.X_OK,
            )

        except OSError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="DIRECTORY_NOT_ACCESSIBLE",
                message=f"Unable to verify directory accessibility: {exc}",
                path=path,
                entry_type="directory",
            )
            return

        if not accessible:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="DIRECTORY_NOT_ACCESSIBLE",
                message="Discovered directory is not accessible.",
                path=path,
                entry_type="directory",
            )

    @staticmethod
    def _check_symlink(
        repository_root: Path,
        path: Path,
        issues: list,
    ) -> None:
        """Validate a discovered symbolic link and its target."""
        if not FileDirectoryIntegrityService._relative_path(
            repository_root,
            path,
            "symlink",
            issues,
        ):
            return

        try:
            metadata = path.lstat()

        except FileNotFoundError:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_MISSING",
                message="Discovered symbolic link no longer exists.",
                path=path,
                entry_type="symlink",
            )
            return

        except PermissionError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_METADATA_ACCESS_DENIED",
                message=(
                    f"Permission denied while reading symbolic-link metadata: {exc}"
                ),
                path=path,
                entry_type="symlink",
            )
            return

        except OSError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_METADATA_READ_FAILED",
                message=f"Unable to read symbolic-link metadata: {exc}",
                path=path,
                entry_type="symlink",
            )
            return

        if not stat.S_ISLNK(metadata.st_mode):
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_TYPE_INVALID",
                message="Discovered symbolic link is no longer a symbolic link.",
                path=path,
                entry_type="symlink",
            )
            return

        try:
            target_exists = path.exists()

        except PermissionError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_TARGET_ACCESS_DENIED",
                message=(
                    f"Permission denied while checking symbolic-link target: {exc}"
                ),
                path=path,
                entry_type="symlink",
            )
            return

        except OSError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_TARGET_ACCESS_FAILED",
                message=f"Unable to inspect symbolic-link target: {exc}",
                path=path,
                entry_type="symlink",
            )
            return

        if not target_exists:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="BROKEN_SYMLINK",
                message="Symbolic link points to a missing target.",
                path=path,
                entry_type="symlink",
            )
            return

        try:
            path.stat()

        except PermissionError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_TARGET_ACCESS_DENIED",
                message=(
                    f"Permission denied while reading symbolic-link target: {exc}"
                ),
                path=path,
                entry_type="symlink",
            )

        except OSError as exc:
            FileDirectoryIntegrityService._add_issue(
                issues=issues,
                code="SYMLINK_TARGET_ACCESS_FAILED",
                message=f"Unable to read symbolic-link target metadata: {exc}",
                path=path,
                entry_type="symlink",
            )
