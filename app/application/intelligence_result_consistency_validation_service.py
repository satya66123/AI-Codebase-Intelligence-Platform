from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class IntelligenceResultConsistencyError(ValueError):
    """Raised when consistency validation receives invalid input."""


class ConsistencySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ConsistencyIssue:
    code: str
    severity: ConsistencySeverity
    artifact_name: str
    message: str
    record_index: int | None = None
    field_name: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise IntelligenceResultConsistencyError(
                "Issue code must be a non-empty string."
            )
        if not isinstance(self.severity, ConsistencySeverity):
            raise IntelligenceResultConsistencyError(
                "Issue severity must be a ConsistencySeverity value."
            )
        if not isinstance(self.artifact_name, str) or not self.artifact_name.strip():
            raise IntelligenceResultConsistencyError(
                "Artifact name must be a non-empty string."
            )
        if not isinstance(self.message, str) or not self.message.strip():
            raise IntelligenceResultConsistencyError(
                "Issue message must be a non-empty string."
            )
        if self.record_index is not None and (
            isinstance(self.record_index, bool)
            or not isinstance(self.record_index, int)
            or self.record_index < 0
        ):
            raise IntelligenceResultConsistencyError(
                "Record index must be a non-negative integer or None."
            )
        if not isinstance(self.field_name, str):
            raise IntelligenceResultConsistencyError(
                "Field name must be a string."
            )


@dataclass(frozen=True)
class IntelligenceResultConsistencyReport:
    artifacts_checked: int
    records_checked: int
    issues: tuple[ConsistencyIssue, ...]
    is_consistent: bool
    error_count: int
    warning_count: int
    info_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "artifacts_checked",
            "records_checked",
            "error_count",
            "warning_count",
            "info_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise IntelligenceResultConsistencyError(
                    f"{field_name} must be a non-negative integer."
                )

        if not isinstance(self.issues, tuple) or not all(
            isinstance(issue, ConsistencyIssue) for issue in self.issues
        ):
            raise IntelligenceResultConsistencyError(
                "Issues must be a tuple of ConsistencyIssue objects."
            )

        if not isinstance(self.is_consistent, bool):
            raise IntelligenceResultConsistencyError(
                "is_consistent must be a boolean."
            )

        expected_errors = sum(
            issue.severity is ConsistencySeverity.ERROR for issue in self.issues
        )
        expected_warnings = sum(
            issue.severity is ConsistencySeverity.WARNING for issue in self.issues
        )
        expected_info = sum(
            issue.severity is ConsistencySeverity.INFO for issue in self.issues
        )

        if (
            self.error_count != expected_errors
            or self.warning_count != expected_warnings
            or self.info_count != expected_info
        ):
            raise IntelligenceResultConsistencyError(
                "Issue counts do not match the supplied issues."
            )

        if self.is_consistent != (self.error_count == 0):
            raise IntelligenceResultConsistencyError(
                "is_consistent must be false when errors exist."
            )

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    def issues_by_severity(
        self,
        severity: ConsistencySeverity,
    ) -> tuple[ConsistencyIssue, ...]:
        if not isinstance(severity, ConsistencySeverity):
            raise IntelligenceResultConsistencyError(
                "Severity must be a ConsistencySeverity value."
            )
        return tuple(
            issue for issue in self.issues if issue.severity is severity
        )


class IntelligenceResultConsistencyValidationService:
    """
    Validates structure and cross-reference consistency across analysis artifacts.

    Each artifact value must be an iterable of records. A record may be a
    mapping, dataclass, or ordinary object with readable attributes.

    Identifiers are checked globally across all artifacts. References are
    resolved against that global identifier set.
    """

    def __init__(
        self,
        required_artifacts: Iterable[str] = (),
        identifier_field: str = "id",
        reference_fields: Iterable[str] = ("references", "related_ids"),
        allow_empty_artifacts: bool = True,
        missing_reference_severity: ConsistencySeverity = ConsistencySeverity.ERROR,
    ) -> None:
        self._required_artifacts = self._validate_name_collection(
            required_artifacts,
            "required_artifacts",
        )
        self._identifier_field = self._validate_field_name(
            identifier_field,
            "identifier_field",
        )
        self._reference_fields = self._validate_name_collection(
            reference_fields,
            "reference_fields",
        )
        self._allow_empty_artifacts = self._validate_boolean(
            allow_empty_artifacts,
            "allow_empty_artifacts",
        )

        if not isinstance(missing_reference_severity, ConsistencySeverity):
            raise IntelligenceResultConsistencyError(
                "missing_reference_severity must be a ConsistencySeverity value."
            )

        self._missing_reference_severity = missing_reference_severity

    def validate(
        self,
        artifacts: Mapping[str, Iterable[object]],
    ) -> IntelligenceResultConsistencyReport:
        """
        Validate artifact collections and references between their records.

        Args:
            artifacts: Mapping of artifact names to iterable record collections.

        Returns:
            A structured consistency report.
        """
        if not isinstance(artifacts, Mapping):
            raise IntelligenceResultConsistencyError(
                "artifacts must be a mapping of names to record collections."
            )

        normalized_artifacts: dict[str, tuple[object, ...]] = {}
        issues: list[ConsistencyIssue] = []

        for artifact_name, records in artifacts.items():
            if not isinstance(artifact_name, str) or not artifact_name.strip():
                raise IntelligenceResultConsistencyError(
                    "Artifact names must be non-empty strings."
                )

            normalized_name = artifact_name.strip()
            if normalized_name in normalized_artifacts:
                raise IntelligenceResultConsistencyError(
                    f"Duplicate artifact name: {normalized_name}."
                )

            normalized_artifacts[normalized_name] = self._materialize_records(
                normalized_name,
                records,
            )

        for required_name in self._required_artifacts:
            if required_name not in normalized_artifacts:
                issues.append(
                    ConsistencyIssue(
                        code="MISSING_REQUIRED_ARTIFACT",
                        severity=ConsistencySeverity.ERROR,
                        artifact_name=required_name,
                        message=f"Required artifact '{required_name}' is missing.",
                    )
                )

        all_identifiers: dict[str, tuple[str, int]] = {}
        record_count = 0

        for artifact_name, records in normalized_artifacts.items():
            if not records and not self._allow_empty_artifacts:
                issues.append(
                    ConsistencyIssue(
                        code="EMPTY_ARTIFACT",
                        severity=ConsistencySeverity.ERROR,
                        artifact_name=artifact_name,
                        message=f"Artifact '{artifact_name}' contains no records.",
                    )
                )

            for index, record in enumerate(records):
                record_count += 1

                if not self._is_record(record):
                    issues.append(
                        ConsistencyIssue(
                            code="INVALID_RECORD",
                            severity=ConsistencySeverity.ERROR,
                            artifact_name=artifact_name,
                            message="Record must be a mapping or an object.",
                            record_index=index,
                        )
                    )
                    continue

                identifier = self._get_value(record, self._identifier_field)

                if not isinstance(identifier, str) or not identifier.strip():
                    issues.append(
                        ConsistencyIssue(
                            code="MISSING_OR_INVALID_IDENTIFIER",
                            severity=ConsistencySeverity.ERROR,
                            artifact_name=artifact_name,
                            message=(
                                f"Record must contain a non-empty string "
                                f"'{self._identifier_field}' field."
                            ),
                            record_index=index,
                            field_name=self._identifier_field,
                        )
                    )
                    continue

                normalized_identifier = identifier.strip()

                if normalized_identifier in all_identifiers:
                    previous_artifact, previous_index = all_identifiers[
                        normalized_identifier
                    ]
                    issues.append(
                        ConsistencyIssue(
                            code="DUPLICATE_IDENTIFIER",
                            severity=ConsistencySeverity.ERROR,
                            artifact_name=artifact_name,
                            message=(
                                f"Identifier '{normalized_identifier}' is duplicated. "
                                f"First occurrence: '{previous_artifact}' "
                                f"record {previous_index}."
                            ),
                            record_index=index,
                            field_name=self._identifier_field,
                        )
                    )
                else:
                    all_identifiers[normalized_identifier] = (
                        artifact_name,
                        index,
                    )

        for artifact_name, records in normalized_artifacts.items():
            for index, record in enumerate(records):
                if not self._is_record(record):
                    continue

                for field_name in self._reference_fields:
                    references = self._get_value(record, field_name)

                    if references is None:
                        continue

                    if isinstance(references, str):
                        references = (references,)

                    if not isinstance(references, (tuple, list, set, frozenset)):
                        issues.append(
                            ConsistencyIssue(
                                code="INVALID_REFERENCE_COLLECTION",
                                severity=ConsistencySeverity.ERROR,
                                artifact_name=artifact_name,
                                message=(
                                    f"Reference field '{field_name}' must contain "
                                    "a string or a collection of strings."
                                ),
                                record_index=index,
                                field_name=field_name,
                            )
                        )
                        continue

                    seen_references: set[str] = set()

                    for reference in references:
                        if not isinstance(reference, str) or not reference.strip():
                            issues.append(
                                ConsistencyIssue(
                                    code="INVALID_REFERENCE",
                                    severity=ConsistencySeverity.ERROR,
                                    artifact_name=artifact_name,
                                    message=(
                                        f"Reference field '{field_name}' contains "
                                        "an empty or non-string reference."
                                    ),
                                    record_index=index,
                                    field_name=field_name,
                                )
                            )
                            continue

                        normalized_reference = reference.strip()

                        if normalized_reference in seen_references:
                            issues.append(
                                ConsistencyIssue(
                                    code="DUPLICATE_REFERENCE",
                                    severity=ConsistencySeverity.WARNING,
                                    artifact_name=artifact_name,
                                    message=(
                                        f"Reference '{normalized_reference}' is "
                                        f"repeated in '{field_name}'."
                                    ),
                                    record_index=index,
                                    field_name=field_name,
                                )
                            )
                            continue

                        seen_references.add(normalized_reference)

                        if normalized_reference not in all_identifiers:
                            issues.append(
                                ConsistencyIssue(
                                    code="UNRESOLVED_REFERENCE",
                                    severity=self._missing_reference_severity,
                                    artifact_name=artifact_name,
                                    message=(
                                        f"Reference '{normalized_reference}' in "
                                        f"'{field_name}' does not match any "
                                        "known identifier."
                                    ),
                                    record_index=index,
                                    field_name=field_name,
                                )
                            )

        issue_tuple = tuple(issues)
        error_count = sum(
            issue.severity is ConsistencySeverity.ERROR for issue in issue_tuple
        )
        warning_count = sum(
            issue.severity is ConsistencySeverity.WARNING for issue in issue_tuple
        )
        info_count = sum(
            issue.severity is ConsistencySeverity.INFO for issue in issue_tuple
        )

        return IntelligenceResultConsistencyReport(
            artifacts_checked=len(normalized_artifacts),
            records_checked=record_count,
            issues=issue_tuple,
            is_consistent=error_count == 0,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
        )

    @staticmethod
    def _materialize_records(
        artifact_name: str,
        records: Iterable[object],
    ) -> tuple[object, ...]:
        if isinstance(records, (str, bytes, Mapping)):
            raise IntelligenceResultConsistencyError(
                f"Artifact '{artifact_name}' must contain an iterable of records, "
                "not a string, bytes, or mapping."
            )

        if not isinstance(records, Iterable):
            raise IntelligenceResultConsistencyError(
                f"Artifact '{artifact_name}' must contain an iterable of records."
            )

        try:
            return tuple(records)
        except Exception as exc:
            raise IntelligenceResultConsistencyError(
                f"Could not read records from artifact '{artifact_name}'."
            ) from exc

    @staticmethod
    def _is_record(record: object) -> bool:
        return isinstance(record, Mapping) or hasattr(record, "__dict__")

    @staticmethod
    def _get_value(record: object, field_name: str) -> Any:
        if isinstance(record, Mapping):
            return record.get(field_name)
        return getattr(record, field_name, None)

    @staticmethod
    def _validate_name_collection(
        values: Iterable[str],
        field_name: str,
    ) -> tuple[str, ...]:
        if isinstance(values, (str, bytes)):
            raise IntelligenceResultConsistencyError(
                f"{field_name} must be an iterable of strings, not a string."
            )

        try:
            materialized = tuple(values)
        except TypeError as exc:
            raise IntelligenceResultConsistencyError(
                f"{field_name} must be iterable."
            ) from exc

        normalized: list[str] = []
        for value in materialized:
            if not isinstance(value, str) or not value.strip():
                raise IntelligenceResultConsistencyError(
                    f"Every value in {field_name} must be a non-empty string."
                )
            normalized.append(value.strip())

        if len(normalized) != len(set(normalized)):
            raise IntelligenceResultConsistencyError(
                f"{field_name} cannot contain duplicate values."
            )

        return tuple(normalized)

    @staticmethod
    def _validate_field_name(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise IntelligenceResultConsistencyError(
                f"{field_name} must be a non-empty string."
            )
        return value.strip()

    @staticmethod
    def _validate_boolean(value: bool, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise IntelligenceResultConsistencyError(
                f"{field_name} must be a boolean."
            )
        return value