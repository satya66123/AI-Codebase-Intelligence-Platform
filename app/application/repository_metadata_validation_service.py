
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from collections import Counter
from typing import Any

from app.application.repository_input import RepositoryInfo
from app.application.repository_scanner import RepositoryScanResult
from app.application.metadata_extraction_service import FileMetadata


class RepositoryMetadataValidationError(ValueError):
    """Raised when repository metadata validation cannot proceed."""


@dataclass(frozen=True)
class RepositoryMetadataIssue:
    """Represents a repository metadata validation issue."""

    code: str
    message: str
    path: str = ""

    def __post_init__(self):
        if not isinstance(self.code, str) or not self.code.strip():
            raise RepositoryMetadataValidationError(
                "Issue code must be a non-empty string."
            )

        if not isinstance(self.message, str) or not self.message.strip():
            raise RepositoryMetadataValidationError(
                "Issue message must be a non-empty string."
            )

        if not isinstance(self.path, str):
            raise RepositoryMetadataValidationError(
                "Issue path must be a string."
            )


@dataclass(frozen=True)
class RepositoryMetadataValidationResult:
    """Immutable result of repository metadata validation."""

    repository_root: Path
    is_valid: bool
    files_validated: int
    directories_validated: int
    symlinks_validated: int
    issues: tuple[RepositoryMetadataIssue, ...]

    def __post_init__(self):
        if not isinstance(self.repository_root, Path):
            raise RepositoryMetadataValidationError(
                "Repository root must be a Path."
            )

        if not isinstance(self.is_valid, bool):
            raise RepositoryMetadataValidationError(
                "is_valid must be a boolean."
            )

        for field_name in (
            "files_validated",
            "directories_validated",
            "symlinks_validated",
        ):
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, int):
                raise RepositoryMetadataValidationError(
                    f"{field_name} must be an integer."
                )

            if value < 0:
                raise RepositoryMetadataValidationError(
                    f"{field_name} cannot be negative."
                )

        if not isinstance(self.issues, tuple):
            raise RepositoryMetadataValidationError(
                "Issues must be provided as a tuple."
            )

        if not all(
            isinstance(issue, RepositoryMetadataIssue)
            for issue in self.issues
        ):
            raise RepositoryMetadataValidationError(
                "Every issue must be a RepositoryMetadataIssue."
            )

        if self.is_valid != (len(self.issues) == 0):
            raise RepositoryMetadataValidationError(
                "is_valid must be true exactly when there are no issues."
            )

    @property
    def total_validated(self) -> int:
        return (
            self.files_validated
            + self.directories_validated
            + self.symlinks_validated
        )

    @property
    def error_count(self) -> int:
        return len(self.issues)

    @property
    def healthy(self) -> bool:
        return self.is_valid


class RepositoryMetadataValidationService:
    """
    Validates metadata produced by MetadataExtractionService.

    Expected metadata structure:

    {
        "repository_name": str,
        "repository_path": str,
        "total_files": int,
        "total_directories": int,
        "total_symlinks": int,
        "total_size_bytes": int,
        "languages": dict,
        "files": list[FileMetadata]
    }

    The service validates metadata completeness and consistency
    against the supplied repository information and scan result.
    """

    REQUIRED_FIELDS = (
        "repository_name",
        "repository_path",
        "total_files",
        "total_directories",
        "total_symlinks",
        "total_size_bytes",
        "languages",
        "files",
    )

    def validate(
        self,
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
        metadata: dict,
    ) -> RepositoryMetadataValidationResult:
        """
        Validate repository metadata against repository discovery data.

        Args:
            repository: Validated repository information.
            scan_result: Repository scanner result.
            metadata: Dictionary returned by MetadataExtractionService.

        Returns:
            RepositoryMetadataValidationResult.

        Raises:
            RepositoryMetadataValidationError:
                If the supplied input objects have invalid types or
                incompatible repository roots.
        """
        self._validate_inputs(
            repository,
            scan_result,
            metadata,
        )

        repository_root = repository.root.resolve(strict=False)
        scan_root = scan_result.root.resolve(strict=False)

        if repository_root != scan_root:
            raise RepositoryMetadataValidationError(
                "Repository root does not match scan result root."
            )

        issues = []

        if not self._validate_required_fields(metadata, issues):
            return self._build_result(
                repository,
                scan_result,
                issues,
            )

        self._validate_repository_identity(
            repository,
            metadata,
            issues,
        )

        self._validate_aggregate_counts(
            scan_result,
            metadata,
            issues,
        )

        self._validate_file_metadata(
            repository,
            scan_result,
            metadata,
            issues,
        )

        self._validate_total_size(
            metadata,
            issues,
        )

        self._validate_language_statistics(
            metadata,
            issues,
        )

        return self._build_result(
            repository,
            scan_result,
            issues,
        )

    @staticmethod
    def _validate_inputs(
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
        metadata: dict,
    ) -> None:
        """Validate the input object types and scan structure."""
        if not isinstance(repository, RepositoryInfo):
            raise RepositoryMetadataValidationError(
                "repository must be a RepositoryInfo instance."
            )

        if not isinstance(scan_result, RepositoryScanResult):
            raise RepositoryMetadataValidationError(
                "scan_result must be a RepositoryScanResult instance."
            )

        if not isinstance(repository.root, Path):
            raise RepositoryMetadataValidationError(
                "Repository root must be a Path."
            )

        if not isinstance(scan_result.root, Path):
            raise RepositoryMetadataValidationError(
                "Scan root must be a Path."
            )

        for field_name in ("files", "directories", "symlinks"):
            entries = getattr(scan_result, field_name)

            if not isinstance(entries, tuple):
                raise RepositoryMetadataValidationError(
                    f"Scan result {field_name} must be a tuple."
                )

            if not all(isinstance(item, Path) for item in entries):
                raise RepositoryMetadataValidationError(
                    f"Every scan result {field_name} entry must be a Path."
                )

        if not isinstance(metadata, dict):
            raise RepositoryMetadataValidationError(
                "metadata must be a dictionary."
            )

    def _validate_required_fields(
        self,
        metadata: dict,
        issues: list,
    ) -> bool:
        """Check required metadata fields and basic container types."""
        missing_fields = [
            field
            for field in self.REQUIRED_FIELDS
            if field not in metadata
        ]

        for field in missing_fields:
            self._add_issue(
                issues,
                "METADATA_FIELD_MISSING",
                f"Required metadata field is missing: {field}.",
                field,
            )

        if missing_fields:
            return False

        string_fields = (
            "repository_name",
            "repository_path",
        )

        for field in string_fields:
            value = metadata[field]

            if not isinstance(value, str) or not value.strip():
                self._add_issue(
                    issues,
                    "METADATA_FIELD_INVALID",
                    f"{field} must be a non-empty string.",
                    field,
                )

        integer_fields = (
            "total_files",
            "total_directories",
            "total_symlinks",
            "total_size_bytes",
        )

        for field in integer_fields:
            value = metadata[field]

            if isinstance(value, bool) or not isinstance(value, int):
                self._add_issue(
                    issues,
                    "METADATA_FIELD_INVALID",
                    f"{field} must be an integer.",
                    field,
                )
            elif value < 0:
                self._add_issue(
                    issues,
                    "METADATA_FIELD_INVALID",
                    f"{field} cannot be negative.",
                    field,
                )

        if not isinstance(metadata["languages"], dict):
            self._add_issue(
                issues,
                "LANGUAGE_METADATA_INVALID",
                "languages must be a dictionary.",
                "languages",
            )

        if not isinstance(metadata["files"], list):
            self._add_issue(
                issues,
                "FILE_METADATA_COLLECTION_INVALID",
                "files must be a list.",
                "files",
            )

        return True

    def _validate_repository_identity(
        self,
        repository: RepositoryInfo,
        metadata: dict,
        issues: list,
    ) -> None:
        """Validate repository name and root path."""
        repository_name = metadata["repository_name"]
        repository_path = metadata["repository_path"]

        if (
            isinstance(repository_name, str)
            and repository_name.strip()
            and repository_name != repository.name
        ):
            self._add_issue(
                issues,
                "REPOSITORY_NAME_MISMATCH",
                "Repository metadata name does not match RepositoryInfo.",
                "repository_name",
            )

        if isinstance(repository_path, str) and repository_path.strip():
            try:
                metadata_root = Path(repository_path).resolve(
                    strict=False
                )
            except (OSError, ValueError):
                self._add_issue(
                    issues,
                    "REPOSITORY_PATH_INVALID",
                    "Repository metadata path is invalid.",
                    "repository_path",
                )
            else:
                expected_root = repository.root.resolve(strict=False)

                if metadata_root != expected_root:
                    self._add_issue(
                        issues,
                        "REPOSITORY_PATH_MISMATCH",
                        "Repository metadata path does not match RepositoryInfo.",
                        "repository_path",
                    )

    def _validate_aggregate_counts(
        self,
        scan_result: RepositoryScanResult,
        metadata: dict,
        issues: list,
    ) -> None:
        """Compare aggregate counts with the scanner result."""
        expected_counts = {
            "total_files": len(scan_result.files),
            "total_directories": len(scan_result.directories),
            "total_symlinks": len(scan_result.symlinks),
        }

        for field, expected in expected_counts.items():
            actual = metadata[field]

            if (
                isinstance(actual, int)
                and not isinstance(actual, bool)
                and actual >= 0
                and actual != expected
            ):
                self._add_issue(
                    issues,
                    "REPOSITORY_COUNT_MISMATCH",
                    (
                        f"{field} is {actual}, but the scan result "
                        f"contains {expected}."
                    ),
                    field,
                )

    def _validate_file_metadata(
        self,
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
        metadata: dict,
        issues: list,
    ) -> None:
        """Validate every FileMetadata record against discovered files."""
        file_records = metadata["files"]

        if not isinstance(file_records, list):
            return

        expected_files = {}

        for file_path in scan_result.files:
            try:
                relative_path = file_path.relative_to(
                    repository.root
                ).as_posix()
            except ValueError:
                self._add_issue(
                    issues,
                    "SCANNED_FILE_OUTSIDE_REPOSITORY",
                    "A scanned file is outside the repository root.",
                    str(file_path),
                )
                continue

            if relative_path in expected_files:
                self._add_issue(
                    issues,
                    "DUPLICATE_SCANNED_FILE",
                    "The scan result contains a duplicate file path.",
                    relative_path,
                )
                continue

            expected_files[relative_path] = file_path

        seen_paths = set()
        valid_records = []

        for index, record in enumerate(file_records):
            record_label = f"files[{index}]"

            if not isinstance(record, FileMetadata):
                self._add_issue(
                    issues,
                    "FILE_METADATA_RECORD_INVALID",
                    "File metadata entry must be a FileMetadata instance.",
                    record_label,
                )
                continue

            if not self._validate_file_record_fields(
                record,
                record_label,
                issues,
            ):
                continue

            relative_path = record.relative_path

            if relative_path in seen_paths:
                self._add_issue(
                    issues,
                    "DUPLICATE_FILE_METADATA",
                    "Duplicate file metadata record detected.",
                    relative_path,
                )
                continue

            seen_paths.add(relative_path)

            expected_path = expected_files.get(relative_path)

            if expected_path is None:
                self._add_issue(
                    issues,
                    "FILE_METADATA_NOT_IN_SCAN",
                    "File metadata does not correspond to a scanned file.",
                    relative_path,
                )
                continue

            self._validate_file_record_consistency(
                record,
                expected_path,
                issues,
            )

            valid_records.append(record)

        for relative_path in expected_files:
            if relative_path not in seen_paths:
                self._add_issue(
                    issues,
                    "FILE_METADATA_MISSING",
                    "Scanned file has no corresponding metadata record.",
                    relative_path,
                )

        self._validate_file_record_count(
            metadata,
            len(file_records),
            len(scan_result.files),
            issues,
        )

    @staticmethod
    def _validate_file_record_fields(
        record: FileMetadata,
        record_label: str,
        issues: list,
    ) -> bool:
        """Validate individual FileMetadata field types and values."""
        valid = True

        text_fields = (
            "name",
            "relative_path",
            "extension",
            "language",
            "modified_time",
        )

        for field in text_fields:
            value = getattr(record, field)

            if not isinstance(value, str) or not value.strip():
                RepositoryMetadataValidationService._add_issue(
                    issues,
                    "FILE_METADATA_FIELD_INVALID",
                    f"{record_label}.{field} must be a non-empty string.",
                    record_label,
                )
                valid = False

        if (
            isinstance(record.size_bytes, bool)
            or not isinstance(record.size_bytes, int)
            or record.size_bytes < 0
        ):
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_SIZE_INVALID",
                f"{record_label}.size_bytes must be a non-negative integer.",
                record_label,
            )
            valid = False

        if not valid:
            return False

        normalized = PurePosixPath(record.relative_path)

        if (
            normalized.is_absolute()
            or ".." in normalized.parts
            or "." in normalized.parts
            or normalized.as_posix() != record.relative_path
            or "\\" in record.relative_path
        ):
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_PATH_INVALID",
                "File metadata relative_path must be a normalized relative POSIX path.",
                record.relative_path,
            )
            return False

        try:
            datetime.fromisoformat(record.modified_time)
        except ValueError:
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_TIME_INVALID",
                "File modification time must be a valid ISO 8601 timestamp.",
                record.relative_path,
            )
            valid = False

        return valid

    @staticmethod
    def _validate_file_record_consistency(
        record: FileMetadata,
        expected_path: Path,
        issues: list,
    ) -> None:
        """Cross-check file metadata against the scanned file."""
        if record.name != expected_path.name:
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_NAME_MISMATCH",
                "File metadata name does not match the scanned file.",
                record.relative_path,
            )

        expected_extension = expected_path.suffix.lower()

        if record.extension != expected_extension:
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_EXTENSION_MISMATCH",
                "File metadata extension does not match the scanned file.",
                record.relative_path,
            )

        try:
            actual_size = expected_path.stat().st_size
        except OSError:
            # Filesystem accessibility is handled by the integrity service.
            # This service validates metadata consistency when stat succeeds.
            return

        if record.size_bytes != actual_size:
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_SIZE_MISMATCH",
                (
                    f"File metadata size is {record.size_bytes}, "
                    f"but the scanned file size is {actual_size}."
                ),
                record.relative_path,
            )

    @staticmethod
    def _validate_file_record_count(
        metadata: dict,
        actual_record_count: int,
        expected_file_count: int,
        issues: list,
    ) -> None:
        """Ensure the file metadata collection matches the scan."""
        total_files = metadata["total_files"]

        if (
            isinstance(total_files, int)
            and not isinstance(total_files, bool)
            and total_files >= 0
            and actual_record_count != total_files
        ):
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_COUNT_MISMATCH",
                (
                    f"Metadata contains {actual_record_count} file records, "
                    f"but total_files is {total_files}."
                ),
                "files",
            )

        if actual_record_count != expected_file_count:
            RepositoryMetadataValidationService._add_issue(
                issues,
                "FILE_METADATA_SCAN_COUNT_MISMATCH",
                (
                    f"Metadata contains {actual_record_count} file records, "
                    f"but the scan contains {expected_file_count} files."
                ),
                "files",
            )

    def _validate_total_size(
        self,
        metadata: dict,
        issues: list,
    ) -> None:
        """Check total repository size against file metadata records."""
        records = metadata["files"]

        if not isinstance(records, list):
            return

        sizes = []

        for record in records:
            if not isinstance(record, FileMetadata):
                continue

            if (
                isinstance(record.size_bytes, int)
                and not isinstance(record.size_bytes, bool)
                and record.size_bytes >= 0
            ):
                sizes.append(record.size_bytes)

        if len(sizes) != len(records):
            return

        total_size = metadata["total_size_bytes"]

        if (
            isinstance(total_size, int)
            and not isinstance(total_size, bool)
            and total_size >= 0
        ):
            expected_size = sum(sizes)

            if total_size != expected_size:
                self._add_issue(
                    issues,
                    "TOTAL_SIZE_MISMATCH",
                    (
                        f"total_size_bytes is {total_size}, "
                        f"but file metadata totals {expected_size}."
                    ),
                    "total_size_bytes",
                )

    def _validate_language_statistics(
        self,
        metadata: dict,
        issues: list,
    ) -> None:
        """Compare language counts with individual file metadata."""
        languages = metadata["languages"]
        records = metadata["files"]

        if not isinstance(languages, dict):
            return

        if not isinstance(records, list):
            return

        for language, count in languages.items():
            if (
                not isinstance(language, str)
                or not language.strip()
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
            ):
                self._add_issue(
                    issues,
                    "LANGUAGE_STATISTICS_INVALID",
                    "Language names must be non-empty strings and counts non-negative integers.",
                    "languages",
                )
                return

        valid_records = [
            record
            for record in records
            if isinstance(record, FileMetadata)
            and isinstance(record.language, str)
            and record.language.strip()
        ]

        expected_counts = dict(
            sorted(
                Counter(
                    record.language
                    for record in valid_records
                ).items()
            )
        )

        actual_counts = dict(sorted(languages.items()))

        if actual_counts != expected_counts:
            self._add_issue(
                issues,
                "LANGUAGE_STATISTICS_MISMATCH",
                (
                    "Language statistics do not match the languages "
                    "in individual file metadata records."
                ),
                "languages",
            )

    @staticmethod
    def _add_issue(
        issues: list,
        code: str,
        message: str,
        path: str = "",
    ) -> None:
        """Append a metadata validation issue."""
        issues.append(
            RepositoryMetadataIssue(
                code=code,
                message=message,
                path=path,
            )
        )

    @staticmethod
    def _build_result(
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
        issues: list,
    ) -> RepositoryMetadataValidationResult:
        """Build the immutable validation result."""
        issue_tuple = tuple(issues)

        return RepositoryMetadataValidationResult(
            repository_root=repository.root,
            is_valid=len(issue_tuple) == 0,
            files_validated=len(scan_result.files),
            directories_validated=len(scan_result.directories),
            symlinks_validated=len(scan_result.symlinks),
            issues=issue_tuple,
        )
