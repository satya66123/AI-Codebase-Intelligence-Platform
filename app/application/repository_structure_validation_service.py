
"""Validate repository structure using existing discovery results."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable
import ntpath
import posixpath

from app.application.repository_input import RepositoryInfo
from app.application.repository_scanner import RepositoryScanResult


class RepositoryStructureValidationError(ValueError):
    """Raised when repository structure validation input is invalid."""


class StructureIssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class RepositoryStructureIssue:
    """A single repository structure validation finding."""

    code: str
    message: str
    path: str = ""
    severity: StructureIssueSeverity = StructureIssueSeverity.ERROR

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise RepositoryStructureValidationError(
                "Issue code must be a non-empty string."
            )

        if not isinstance(self.message, str) or not self.message.strip():
            raise RepositoryStructureValidationError(
                "Issue message must be a non-empty string."
            )

        if not isinstance(self.path, str):
            raise RepositoryStructureValidationError(
                "Issue path must be a string."
            )

        if not isinstance(self.severity, StructureIssueSeverity):
            raise RepositoryStructureValidationError(
                "Issue severity must be a StructureIssueSeverity."
            )


@dataclass(frozen=True)
class RepositoryStructureValidationResult:
    """Result of validating a repository's discovered structure."""

    repository_root: Path
    is_valid: bool
    total_files: int
    total_directories: int
    total_symlinks: int
    issues: tuple[RepositoryStructureIssue, ...]

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity == StructureIssueSeverity.ERROR
            for issue in self.issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity == StructureIssueSeverity.WARNING
            for issue in self.issues
        )

    @property
    def missing_count(self) -> int:
        return sum(
            issue.code in {
                "MISSING_REQUIRED_FILE",
                "MISSING_REQUIRED_DIRECTORY",
            }
            for issue in self.issues
        )


class RepositoryStructureValidationService:
    """Validate repository structure without performing another scan.

    Required files and directories are repository-relative paths.
    No repository layout is assumed by default.
    """

    def validate(
        self,
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
        required_files: Iterable[str | Path] = (),
        required_directories: Iterable[str | Path] = (),
    ) -> RepositoryStructureValidationResult:
        """Validate scan consistency and caller-specified required paths."""

        self._validate_inputs(repository, scan_result)

        root = repository.root
        issues: list[RepositoryStructureIssue] = []

        self._validate_scan_root(root, scan_result, issues)

        self._validate_entries(
            root=root,
            entries=scan_result.files,
            expected_type="file",
            issues=issues,
        )

        self._validate_entries(
            root=root,
            entries=scan_result.directories,
            expected_type="directory",
            issues=issues,
        )

        self._validate_entries(
            root=root,
            entries=scan_result.symlinks,
            expected_type="symlink",
            issues=issues,
        )

        self._validate_cross_category_duplicates(
            scan_result.files,
            scan_result.directories,
            scan_result.symlinks,
            issues,
        )

        self._validate_required_paths(
            root=root,
            required_paths=required_files,
            expected_type="file",
            issues=issues,
        )

        self._validate_required_paths(
            root=root,
            required_paths=required_directories,
            expected_type="directory",
            issues=issues,
        )

        error_count = sum(
            issue.severity == StructureIssueSeverity.ERROR
            for issue in issues
        )

        return RepositoryStructureValidationResult(
            repository_root=root,
            is_valid=error_count == 0,
            total_files=len(scan_result.files),
            total_directories=len(scan_result.directories),
            total_symlinks=len(scan_result.symlinks),
            issues=tuple(issues),
        )

    @staticmethod
    def _validate_inputs(
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
    ) -> None:
        if not isinstance(repository, RepositoryInfo):
            raise RepositoryStructureValidationError(
                "A valid RepositoryInfo object is required."
            )

        if not isinstance(scan_result, RepositoryScanResult):
            raise RepositoryStructureValidationError(
                "A valid RepositoryScanResult object is required."
            )

        if not isinstance(repository.root, Path):
            raise RepositoryStructureValidationError(
                "Repository root must be a Path."
            )

        if not isinstance(scan_result.root, Path):
            raise RepositoryStructureValidationError(
                "Scan result root must be a Path."
            )

        for field_name in ("files", "directories", "symlinks"):
            value = getattr(scan_result, field_name)

            if not isinstance(value, tuple):
                raise RepositoryStructureValidationError(
                    f"Scan result {field_name} must be a tuple."
                )

            if not all(isinstance(path, Path) for path in value):
                raise RepositoryStructureValidationError(
                    f"Every scan result {field_name} entry must be a Path."
                )

    @staticmethod
    def _validate_scan_root(
        root: Path,
        scan_result: RepositoryScanResult,
        issues: list[RepositoryStructureIssue],
    ) -> None:
        try:
            repository_root = root.resolve()
            scanned_root = scan_result.root.resolve()
        except (OSError, RuntimeError):
            issues.append(
                RepositoryStructureIssue(
                    code="ROOT_RESOLUTION_FAILED",
                    message=(
                        "Unable to resolve repository or scan-result root."
                    ),
                    path=str(root),
                )
            )
            return

        if repository_root != scanned_root:
            issues.append(
                RepositoryStructureIssue(
                    code="SCAN_ROOT_MISMATCH",
                    message=(
                        "Scan result root does not match the repository root."
                    ),
                    path=str(scan_result.root),
                )
            )

    @staticmethod
    def _validate_entries(
        root: Path,
        entries: tuple[Path, ...],
        expected_type: str,
        issues: list[RepositoryStructureIssue],
    ) -> None:
        seen: set[Path] = set()

        for entry in entries:
            display_path = str(entry)

            try:
                relative_path = entry.relative_to(root)
            except ValueError:
                issues.append(
                    RepositoryStructureIssue(
                        code="ENTRY_OUTSIDE_REPOSITORY",
                        message=(
                            "Discovered entry is outside the repository root."
                        ),
                        path=display_path,
                    )
                )
                continue

            if entry in seen:
                issues.append(
                    RepositoryStructureIssue(
                        code="DUPLICATE_ENTRY",
                        message=(
                            "The scan result contains a duplicate entry."
                        ),
                        path=display_path,
                    )
                )
                continue

            seen.add(entry)

            if relative_path == Path("."):
                issues.append(
                    RepositoryStructureIssue(
                        code="INVALID_ROOT_ENTRY",
                        message=(
                            "The repository root cannot be a discovered "
                            "child entry."
                        ),
                        path=display_path,
                    )
                )
                continue

            if not entry.exists() and not entry.is_symlink():
                issues.append(
                    RepositoryStructureIssue(
                        code="DISCOVERED_ENTRY_MISSING",
                        message="A discovered entry no longer exists.",
                        path=display_path,
                    )
                )
                continue

            if expected_type == "file" and not entry.is_file():
                issues.append(
                    RepositoryStructureIssue(
                        code="ENTRY_TYPE_MISMATCH",
                        message=(
                            "A discovered file is not currently a file."
                        ),
                        path=display_path,
                    )
                )

            elif expected_type == "directory" and not entry.is_dir():
                issues.append(
                    RepositoryStructureIssue(
                        code="ENTRY_TYPE_MISMATCH",
                        message=(
                            "A discovered directory is not currently "
                            "a directory."
                        ),
                        path=display_path,
                    )
                )

            elif expected_type == "symlink" and not entry.is_symlink():
                issues.append(
                    RepositoryStructureIssue(
                        code="ENTRY_TYPE_MISMATCH",
                        message=(
                            "A discovered symbolic link is not currently "
                            "a symlink."
                        ),
                        path=display_path,
                    )
                )

    @staticmethod
    def _validate_cross_category_duplicates(
        files: tuple[Path, ...],
        directories: tuple[Path, ...],
        symlinks: tuple[Path, ...],
        issues: list[RepositoryStructureIssue],
    ) -> None:
        categories = (
            ("file", files),
            ("directory", directories),
            ("symlink", symlinks),
        )

        seen: dict[Path, str] = {}

        for category, entries in categories:
            for entry in entries:
                previous_category = seen.get(entry)

                if previous_category is not None:
                    issues.append(
                        RepositoryStructureIssue(
                            code="ENTRY_CATEGORY_CONFLICT",
                            message=(
                                f"Entry is listed as both {previous_category} "
                                f"and {category}."
                            ),
                            path=str(entry),
                        )
                    )
                else:
                    seen[entry] = category

    @staticmethod
    def _normalize_required_paths(
        required_paths: Iterable[str | Path],
        expected_type: str,
    ) -> tuple[Path, ...]:
        if isinstance(required_paths, (str, bytes, Path)):
            raise RepositoryStructureValidationError(
                f"required_{expected_type}s must be an iterable "
                "of relative paths."
            )

        try:
            values = tuple(required_paths)
        except TypeError as exc:
            raise RepositoryStructureValidationError(
                f"required_{expected_type}s must be iterable."
            ) from exc

        normalized: list[Path] = []

        for value in values:
            if not isinstance(value, (str, Path)):
                raise RepositoryStructureValidationError(
                    "Required paths must be strings or Path objects."
                )

            raw_value = str(value)

            if not raw_value.strip():
                raise RepositoryStructureValidationError(
                    "Required paths must be non-empty relative paths."
                )

            if (
                Path(raw_value).is_absolute()
                or ntpath.isabs(raw_value)
                or posixpath.isabs(raw_value)
                or ntpath.splitdrive(raw_value)[0]
            ):
                raise RepositoryStructureValidationError(
                    "Required paths must be relative paths."
                )

            path = Path(raw_value)

            normalized_parts = raw_value.replace("\\", "/").split("/")

            if ".." in path.parts or ".." in normalized_parts:
                raise RepositoryStructureValidationError(
                    "Required paths cannot contain parent-directory "
                    "traversal."
                )

            if path == Path("."):
                raise RepositoryStructureValidationError(
                    "The repository root cannot be a required child path."
                )

            normalized.append(path)

        return tuple(normalized)

    def _validate_required_paths(
        self,
        root: Path,
        required_paths: Iterable[str | Path],
        expected_type: str,
        issues: list[RepositoryStructureIssue],
    ) -> None:
        normalized_paths = self._normalize_required_paths(
            required_paths,
            expected_type,
        )

        seen: set[Path] = set()

        for relative_path in normalized_paths:
            if relative_path in seen:
                continue

            seen.add(relative_path)

            target = root / relative_path
            display_path = relative_path.as_posix()

            if not target.exists():
                issues.append(
                    RepositoryStructureIssue(
                        code=(
                            "MISSING_REQUIRED_FILE"
                            if expected_type == "file"
                            else "MISSING_REQUIRED_DIRECTORY"
                        ),
                        message=f"Required {expected_type} does not exist.",
                        path=display_path,
                    )
                )
                continue

            if expected_type == "file" and not target.is_file():
                issues.append(
                    RepositoryStructureIssue(
                        code="REQUIRED_PATH_TYPE_MISMATCH",
                        message="Required file path is not a file.",
                        path=display_path,
                    )
                )

            elif expected_type == "directory" and not target.is_dir():
                issues.append(
                    RepositoryStructureIssue(
                        code="REQUIRED_PATH_TYPE_MISMATCH",
                        message="Required directory path is not a directory.",
                        path=display_path,
                    )
                )
