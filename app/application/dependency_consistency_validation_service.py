
"""Validate consistency between import analysis and dependency analysis."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from app.application.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyRecord,
)
from app.application.import_analyzer import ImportRecord


class DependencyConsistencyValidationError(ValueError):
    """Raised when dependency consistency validation cannot be performed."""


class DependencyConsistencySeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class DependencyConsistencyIssue:
    """One inconsistency found between import and dependency records."""

    code: str
    message: str
    source_file: str = ""
    line: int = 0
    severity: DependencyConsistencySeverity = DependencyConsistencySeverity.ERROR

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be a non-empty string.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string.")
        if not isinstance(self.source_file, str):
            raise TypeError("source_file must be a string.")
        if (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 0
        ):
            raise ValueError("line must be a non-negative integer.")
        if not isinstance(
            self.severity,
            DependencyConsistencySeverity,
        ):
            raise TypeError(
                "severity must be a DependencyConsistencySeverity."
            )


@dataclass(frozen=True)
class DependencyConsistencyValidationResult:
    """Result of validating import and dependency consistency."""

    is_valid: bool
    imports_checked: int
    dependencies_checked: int
    matched_dependencies: int
    missing_dependencies: int
    unexpected_dependencies: int
    mismatched_classifications: int
    issues: tuple[DependencyConsistencyIssue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.is_valid, bool):
            raise TypeError("is_valid must be a boolean.")

        for name in (
            "imports_checked",
            "dependencies_checked",
            "matched_dependencies",
            "missing_dependencies",
            "unexpected_dependencies",
            "mismatched_classifications",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple.")

        if not all(
            isinstance(issue, DependencyConsistencyIssue)
            for issue in self.issues
        ):
            raise TypeError(
                "issues must contain DependencyConsistencyIssue objects."
            )

        if self.is_valid and self.issues:
            raise ValueError("A valid result cannot contain issues.")

        if not self.is_valid and not self.issues:
            raise ValueError("An invalid result must contain at least one issue.")

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity == DependencyConsistencySeverity.ERROR
            for issue in self.issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity == DependencyConsistencySeverity.WARNING
            for issue in self.issues
        )

    @property
    def healthy(self) -> bool:
        return self.is_valid

    @property
    def total_issues(self) -> int:
        return len(self.issues)


class DependencyConsistencyValidationService:
    """Validate dependency records against their originating import records."""

    VALID_DEPENDENCY_TYPES = {
        DependencyAnalyzer.DEPENDENCY_INTERNAL,
        DependencyAnalyzer.DEPENDENCY_EXTERNAL,
        DependencyAnalyzer.DEPENDENCY_STANDARD_LIBRARY,
        DependencyAnalyzer.DEPENDENCY_UNRESOLVED,
    }

    def __init__(
        self,
        dependency_analyzer: DependencyAnalyzer | None = None,
    ) -> None:
        self.dependency_analyzer = (
            dependency_analyzer or DependencyAnalyzer()
        )

    def validate(
        self,
        imports: Iterable[ImportRecord],
        dependencies: Iterable[DependencyRecord],
        internal_modules: Iterable[str] = (),
    ) -> DependencyConsistencyValidationResult:
        """Validate correspondence and classification of dependency records."""
        import_records = self._materialize_imports(imports)
        dependency_records = self._materialize_dependencies(dependencies)
        known_modules = self._materialize_internal_modules(internal_modules)

        expected_dependencies = self.dependency_analyzer.analyze(
            import_records,
            internal_modules=known_modules,
        )

        import_groups = self._group_imports(import_records)
        dependency_groups = self._group_dependencies(dependency_records)

        issues: list[DependencyConsistencyIssue] = []
        matched_dependencies = 0
        missing_dependencies = 0
        unexpected_dependencies = 0
        mismatched_classifications = 0

        all_keys = sorted(
            set(import_groups) | set(dependency_groups),
            key=self._identity_sort_key,
        )

        for key in all_keys:
            import_group = import_groups.get(key, [])
            dependency_group = dependency_groups.get(key, [])

            if len(import_group) > len(dependency_group):
                missing_count = len(import_group) - len(dependency_group)
                missing_dependencies += missing_count

                for _ in range(missing_count):
                    record = import_group[0]
                    issues.append(
                        DependencyConsistencyIssue(
                            code="MISSING_DEPENDENCY",
                            message=(
                                "An import record has no matching "
                                "dependency record."
                            ),
                            source_file=record.filename,
                            line=record.line,
                        )
                    )

            if len(dependency_group) > len(import_group):
                unexpected_count = len(dependency_group) - len(import_group)
                unexpected_dependencies += unexpected_count

                for _ in range(unexpected_count):
                    record = dependency_group[0]
                    issues.append(
                        DependencyConsistencyIssue(
                            code="UNEXPECTED_DEPENDENCY",
                            message=(
                                "A dependency record has no matching "
                                "import record."
                            ),
                            source_file=record.source_file,
                            line=record.line,
                        )
                    )

            paired_count = min(len(import_group), len(dependency_group))
            matched_dependencies += paired_count

            if paired_count:
                expected_types = sorted(
                    self._expected_types_for_identity(
                        key,
                        expected_dependencies,
                    )
                )
                actual_records = sorted(
                    dependency_group,
                    key=lambda record: record.dependency_type,
                )

                for index in range(paired_count):
                    record = actual_records[index]
                    expected_type = expected_types[index]
                    actual_type = record.dependency_type

                    if actual_type != expected_type:
                        mismatched_classifications += 1
                        issues.append(
                            DependencyConsistencyIssue(
                                code="CLASSIFICATION_MISMATCH",
                                message=(
                                    "Dependency classification does not "
                                    f"match the expected value "
                                    f"'{expected_type}'."
                                ),
                                source_file=record.source_file,
                                line=record.line,
                            )
                        )

        for record in dependency_records:
            if record.dependency_type not in self.VALID_DEPENDENCY_TYPES:
                issues.append(
                    DependencyConsistencyIssue(
                        code="INVALID_DEPENDENCY_TYPE",
                        message=(
                            f"Unsupported dependency type: "
                            f"{record.dependency_type!r}."
                        ),
                        source_file=record.source_file,
                        line=record.line,
                    )
                )

        issues.sort(
            key=lambda issue: (
                issue.source_file,
                issue.line,
                issue.code,
                issue.message,
            )
        )

        return DependencyConsistencyValidationResult(
            is_valid=not issues,
            imports_checked=len(import_records),
            dependencies_checked=len(dependency_records),
            matched_dependencies=matched_dependencies,
            missing_dependencies=missing_dependencies,
            unexpected_dependencies=unexpected_dependencies,
            mismatched_classifications=mismatched_classifications,
            issues=tuple(issues),
        )

    @staticmethod
    def _materialize_imports(
        imports: Iterable[ImportRecord],
    ) -> tuple[ImportRecord, ...]:
        if imports is None or isinstance(imports, (str, bytes, dict, set, frozenset)):
            raise DependencyConsistencyValidationError(
                "imports must be an iterable of ImportRecord objects."
            )

        try:
            records = tuple(imports)
        except TypeError as exc:
            raise DependencyConsistencyValidationError(
                "imports must be iterable."
            ) from exc

        if not all(isinstance(record, ImportRecord) for record in records):
            raise DependencyConsistencyValidationError(
                "Every import must be an ImportRecord."
            )

        for record in records:
            if not isinstance(record.filename, str) or not record.filename.strip():
                raise DependencyConsistencyValidationError(
                    "Import filename must be a non-empty string."
                )
            if (
                isinstance(record.line, bool)
                or not isinstance(record.line, int)
                or record.line < 1
            ):
                raise DependencyConsistencyValidationError(
                    "Import line must be a positive integer."
                )
            if (
                isinstance(record.level, bool)
                or not isinstance(record.level, int)
                or record.level < 0
            ):
                raise DependencyConsistencyValidationError(
                    "Import level must be a non-negative integer."
                )
            if record.import_type not in {"import", "from_import"}:
                raise DependencyConsistencyValidationError(
                    "Import type must be 'import' or 'from_import'."
                )
            if record.module is not None and not isinstance(record.module, str):
                raise DependencyConsistencyValidationError(
                    "Import module must be a string or None."
                )
            if (
                record.imported_name is not None
                and not isinstance(record.imported_name, str)
            ):
                raise DependencyConsistencyValidationError(
                    "Imported name must be a string or None."
                )
            if record.alias is not None and not isinstance(record.alias, str):
                raise DependencyConsistencyValidationError(
                    "Import alias must be a string or None."
                )

        return records

    @staticmethod
    def _materialize_dependencies(
        dependencies: Iterable[DependencyRecord],
    ) -> tuple[DependencyRecord, ...]:
        if dependencies is None or isinstance(
            dependencies,
            (str, bytes, dict, set, frozenset),
        ):
            raise DependencyConsistencyValidationError(
                "dependencies must be an iterable of DependencyRecord objects."
            )

        try:
            records = tuple(dependencies)
        except TypeError as exc:
            raise DependencyConsistencyValidationError(
                "dependencies must be iterable."
            ) from exc

        if not all(isinstance(record, DependencyRecord) for record in records):
            raise DependencyConsistencyValidationError(
                "Every dependency must be a DependencyRecord."
            )

        for record in records:
            if (
                not isinstance(record.source_file, str)
                or not record.source_file.strip()
            ):
                raise DependencyConsistencyValidationError(
                    "Dependency source_file must be a non-empty string."
                )
            if (
                isinstance(record.line, bool)
                or not isinstance(record.line, int)
                or record.line < 1
            ):
                raise DependencyConsistencyValidationError(
                    "Dependency line must be a positive integer."
                )
            if not isinstance(record.is_relative, bool):
                raise DependencyConsistencyValidationError(
                    "Dependency is_relative must be a boolean."
                )
            if (
                record.imported_module is not None
                and not isinstance(record.imported_module, str)
            ):
                raise DependencyConsistencyValidationError(
                    "Dependency imported_module must be a string or None."
                )
            if (
                record.imported_name is not None
                and not isinstance(record.imported_name, str)
            ):
                raise DependencyConsistencyValidationError(
                    "Dependency imported_name must be a string or None."
                )
            if record.alias is not None and not isinstance(record.alias, str):
                raise DependencyConsistencyValidationError(
                    "Dependency alias must be a string or None."
                )
            if not isinstance(record.dependency_type, str):
                raise DependencyConsistencyValidationError(
                    "Dependency type must be a string."
                )

        return records

    @staticmethod
    def _materialize_internal_modules(
        internal_modules: Iterable[str],
    ) -> tuple[str, ...]:
        # Sets are deliberately rejected to keep input validation consistent
        # with the other collection arguments and the test contract.
        if internal_modules is None or isinstance(
            internal_modules,
            (str, bytes, dict, set, frozenset),
        ):
            raise DependencyConsistencyValidationError(
                "internal_modules must be an iterable of module names."
            )

        try:
            modules = tuple(internal_modules)
        except TypeError as exc:
            raise DependencyConsistencyValidationError(
                "internal_modules must be iterable."
            ) from exc

        if not all(
            isinstance(module, str) and module.strip()
            for module in modules
        ):
            raise DependencyConsistencyValidationError(
                "Every internal module must be a non-empty string."
            )

        return modules

    @staticmethod
    def _import_identity(record: ImportRecord) -> tuple:
        return (
            record.filename,
            record.line,
            record.module,
            record.imported_name,
            record.alias,
            record.is_relative,
        )

    @staticmethod
    def _dependency_identity(record: DependencyRecord) -> tuple:
        return (
            record.source_file,
            record.line,
            record.imported_module,
            record.imported_name,
            record.alias,
            record.is_relative,
        )

    @classmethod
    def _group_imports(
        cls,
        records: tuple[ImportRecord, ...],
    ) -> dict[tuple, list[ImportRecord]]:
        groups: dict[tuple, list[ImportRecord]] = defaultdict(list)
        for record in records:
            groups[cls._import_identity(record)].append(record)
        return groups

    @classmethod
    def _group_dependencies(
        cls,
        records: tuple[DependencyRecord, ...],
    ) -> dict[tuple, list[DependencyRecord]]:
        groups: dict[tuple, list[DependencyRecord]] = defaultdict(list)
        for record in records:
            groups[cls._dependency_identity(record)].append(record)
        return groups

    @staticmethod
    def _expected_types_for_identity(
        identity: tuple,
        expected_dependencies: tuple[DependencyRecord, ...],
    ) -> list[str]:
        return [
            record.dependency_type
            for record in expected_dependencies
            if (
                record.source_file,
                record.line,
                record.imported_module,
                record.imported_name,
                record.alias,
                record.is_relative,
            ) == identity
        ]

    @staticmethod
    def _identity_sort_key(identity: tuple) -> tuple[str, ...]:
        return tuple(
            "" if value is None else str(value)
            for value in identity
        )
