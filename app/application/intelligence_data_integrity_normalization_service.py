from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class IntelligenceDataIntegrityError(ValueError):
    """Raised when intelligence data integrity processing receives invalid input."""


class IntegritySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class IntegrityFinding:
    code: str
    severity: IntegritySeverity
    record_index: int
    field_name: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise IntelligenceDataIntegrityError("Finding code must be non-empty.")
        if not isinstance(self.severity, IntegritySeverity):
            raise IntelligenceDataIntegrityError("Invalid finding severity.")
        if (
            isinstance(self.record_index, bool)
            or not isinstance(self.record_index, int)
            or self.record_index < 0
        ):
            raise IntelligenceDataIntegrityError(
                "record_index must be a non-negative integer."
            )
        if not isinstance(self.field_name, str):
            raise IntelligenceDataIntegrityError("field_name must be a string.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise IntelligenceDataIntegrityError("Finding message must be non-empty.")


@dataclass(frozen=True)
class NormalizedIntelligenceRecord:
    record_index: int
    data: Mapping[str, Any]
    changed_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.record_index, bool)
            or not isinstance(self.record_index, int)
            or self.record_index < 0
        ):
            raise IntelligenceDataIntegrityError(
                "record_index must be a non-negative integer."
            )
        if not isinstance(self.data, Mapping):
            raise IntelligenceDataIntegrityError("data must be a mapping.")
        if not isinstance(self.changed_fields, tuple) or not all(
            isinstance(field, str) and field.strip()
            for field in self.changed_fields
        ):
            raise IntelligenceDataIntegrityError(
                "changed_fields must be a tuple of non-empty strings."
            )


@dataclass(frozen=True)
class IntelligenceDataIntegrityReport:
    total_records: int
    normalized_records: int
    invalid_records: int
    duplicate_records: int
    changed_field_count: int
    records: tuple[NormalizedIntelligenceRecord, ...]
    findings: tuple[IntegrityFinding, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "total_records",
            "normalized_records",
            "invalid_records",
            "duplicate_records",
            "changed_field_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise IntelligenceDataIntegrityError(
                    f"{field_name} must be a non-negative integer."
                )

        if self.normalized_records + self.invalid_records != self.total_records:
            raise IntelligenceDataIntegrityError(
                "normalized_records and invalid_records must equal total_records."
            )

        if not isinstance(self.records, tuple) or not all(
            isinstance(record, NormalizedIntelligenceRecord)
            for record in self.records
        ):
            raise IntelligenceDataIntegrityError(
                "records must be a tuple of NormalizedIntelligenceRecord objects."
            )

        if len(self.records) != self.normalized_records:
            raise IntelligenceDataIntegrityError(
                "records length must equal normalized_records."
            )

        if not isinstance(self.findings, tuple) or not all(
            isinstance(finding, IntegrityFinding) for finding in self.findings
        ):
            raise IntelligenceDataIntegrityError(
                "findings must be a tuple of IntegrityFinding objects."
            )

    @property
    def is_valid(self) -> bool:
        return self.invalid_records == 0 and not any(
            finding.severity is IntegritySeverity.ERROR
            for finding in self.findings
        )

    @property
    def has_warnings(self) -> bool:
        return any(
            finding.severity is IntegritySeverity.WARNING
            for finding in self.findings
        )

    @property
    def error_count(self) -> int:
        return sum(
            finding.severity is IntegritySeverity.ERROR
            for finding in self.findings
        )

    @property
    def warning_count(self) -> int:
        return sum(
            finding.severity is IntegritySeverity.WARNING
            for finding in self.findings
        )

    @property
    def info_count(self) -> int:
        return sum(
            finding.severity is IntegritySeverity.INFO
            for finding in self.findings
        )


class IntelligenceDataIntegrityNormalizationService:
    """
    Normalizes and validates intelligence records.

    The service:
    - trims configured string fields,
    - collapses repeated whitespace in configured text fields,
    - normalizes configured repository-relative paths,
    - validates required fields,
    - detects duplicate identifiers,
    - detects conflicting duplicate identifiers.

    Records containing validation errors are excluded from the normalized
    output. Warnings and informational findings do not invalidate a record.
    """

    def __init__(
        self,
        required_fields: Iterable[str] = ("id",),
        text_fields: Iterable[str] = (),
        path_fields: Iterable[str] = ("file_path", "filename"),
        identifier_field: str = "id",
        case_insensitive_identifiers: bool = False,
        reject_absolute_paths: bool = True,
    ) -> None:
        self._required_fields = self._validate_field_collection(
            required_fields, "required_fields"
        )
        self._text_fields = self._validate_field_collection(
            text_fields, "text_fields"
        )
        self._path_fields = self._validate_field_collection(
            path_fields, "path_fields"
        )
        self._identifier_field = self._validate_field_name(
            identifier_field, "identifier_field"
        )
        self._case_insensitive_identifiers = self._validate_boolean(
            case_insensitive_identifiers,
            "case_insensitive_identifiers",
        )
        self._reject_absolute_paths = self._validate_boolean(
            reject_absolute_paths,
            "reject_absolute_paths",
        )

    def normalize(
        self,
        records: Iterable[Mapping[str, Any]],
    ) -> IntelligenceDataIntegrityReport:
        if isinstance(records, (str, bytes, Mapping)):
            raise IntelligenceDataIntegrityError(
                "records must be an iterable of mapping records."
            )

        try:
            input_records = tuple(records)
        except TypeError as exc:
            raise IntelligenceDataIntegrityError(
                "records must be iterable."
            ) from exc

        findings: list[IntegrityFinding] = []
        normalized_records: list[NormalizedIntelligenceRecord] = []
        invalid_record_indexes: set[int] = set()
        identifier_records: dict[str, tuple[int, dict[str, Any]]] = {}
        duplicate_record_indexes: set[int] = set()
        changed_field_count = 0

        for index, record in enumerate(input_records):
            if not isinstance(record, Mapping):
                findings.append(
                    IntegrityFinding(
                        code="INVALID_RECORD_TYPE",
                        severity=IntegritySeverity.ERROR,
                        record_index=index,
                        field_name="",
                        message="Record must be a mapping.",
                    )
                )
                invalid_record_indexes.add(index)
                continue

            normalized = dict(record)
            changed_fields: list[str] = []

            for field_name in self._required_fields:
                if field_name not in normalized or normalized[field_name] is None:
                    findings.append(
                        IntegrityFinding(
                            code="MISSING_REQUIRED_FIELD",
                            severity=IntegritySeverity.ERROR,
                            record_index=index,
                            field_name=field_name,
                            message=f"Required field '{field_name}' is missing.",
                        )
                    )
                    invalid_record_indexes.add(index)

            for field_name in self._text_fields:
                if field_name not in normalized or normalized[field_name] is None:
                    continue

                value = normalized[field_name]
                if not isinstance(value, str):
                    findings.append(
                        IntegrityFinding(
                            code="INVALID_TEXT_FIELD",
                            severity=IntegritySeverity.ERROR,
                            record_index=index,
                            field_name=field_name,
                            message=f"Field '{field_name}' must be a string.",
                        )
                    )
                    invalid_record_indexes.add(index)
                    continue

                normalized_value = " ".join(value.split())
                if normalized_value != value:
                    normalized[field_name] = normalized_value
                    changed_fields.append(field_name)
                    findings.append(
                        IntegrityFinding(
                            code="TEXT_NORMALIZED",
                            severity=IntegritySeverity.INFO,
                            record_index=index,
                            field_name=field_name,
                            message=f"Whitespace was normalized in '{field_name}'.",
                        )
                    )

            for field_name in self._path_fields:
                if field_name not in normalized or normalized[field_name] is None:
                    continue

                value = normalized[field_name]
                if not isinstance(value, str) or not value.strip():
                    findings.append(
                        IntegrityFinding(
                            code="INVALID_PATH_FIELD",
                            severity=IntegritySeverity.ERROR,
                            record_index=index,
                            field_name=field_name,
                            message=f"Path field '{field_name}' must be a non-empty string.",
                        )
                    )
                    invalid_record_indexes.add(index)
                    continue

                path, path_error = self._normalize_path(value)
                if path_error:
                    findings.append(
                        IntegrityFinding(
                            code=path_error,
                            severity=IntegritySeverity.ERROR,
                            record_index=index,
                            field_name=field_name,
                            message=f"Path field '{field_name}' is not a valid relative path.",
                        )
                    )
                    invalid_record_indexes.add(index)
                    continue

                if path != value:
                    normalized[field_name] = path
                    changed_fields.append(field_name)
                    findings.append(
                        IntegrityFinding(
                            code="PATH_NORMALIZED",
                            severity=IntegritySeverity.INFO,
                            record_index=index,
                            field_name=field_name,
                            message=f"Path was normalized in '{field_name}'.",
                        )
                    )

            identifier = normalized.get(self._identifier_field)
            if not isinstance(identifier, str) or not identifier.strip():
                findings.append(
                    IntegrityFinding(
                        code="INVALID_IDENTIFIER",
                        severity=IntegritySeverity.ERROR,
                        record_index=index,
                        field_name=self._identifier_field,
                        message=(
                            f"Identifier field '{self._identifier_field}' "
                            "must be a non-empty string."
                        ),
                    )
                )
                invalid_record_indexes.add(index)
            else:
                normalized_identifier = identifier.strip()
                if normalized_identifier != identifier:
                    normalized[self._identifier_field] = normalized_identifier
                    changed_fields.append(self._identifier_field)
                    findings.append(
                        IntegrityFinding(
                            code="IDENTIFIER_NORMALIZED",
                            severity=IntegritySeverity.INFO,
                            record_index=index,
                            field_name=self._identifier_field,
                            message="Identifier whitespace was trimmed.",
                        )
                    )

                identifier_key = self._identifier_key(normalized_identifier)
                previous = identifier_records.get(identifier_key)

                if previous is not None:
                    previous_index, previous_record = previous
                    duplicate_record_indexes.add(index)

                    if previous_record == normalized:
                        findings.append(
                            IntegrityFinding(
                                code="DUPLICATE_RECORD",
                                severity=IntegritySeverity.WARNING,
                                record_index=index,
                                field_name=self._identifier_field,
                                message=(
                                    f"Record duplicates record {previous_index} "
                                    f"with identifier '{normalized_identifier}'."
                                ),
                            )
                        )
                    else:
                        findings.append(
                            IntegrityFinding(
                                code="CONFLICTING_IDENTIFIER",
                                severity=IntegritySeverity.ERROR,
                                record_index=index,
                                field_name=self._identifier_field,
                                message=(
                                    f"Identifier '{normalized_identifier}' conflicts "
                                    f"with record {previous_index}."
                                ),
                            )
                        )
                        invalid_record_indexes.add(index)
                else:
                    identifier_records[identifier_key] = (index, normalized)

            if index not in invalid_record_indexes:
                normalized_records.append(
                    NormalizedIntelligenceRecord(
                        record_index=index,
                        data=normalized,
                        changed_fields=tuple(dict.fromkeys(changed_fields)),
                    )
                )
                changed_field_count += len(set(changed_fields))

        invalid_count = len(invalid_record_indexes)

        return IntelligenceDataIntegrityReport(
            total_records=len(input_records),
            normalized_records=len(normalized_records),
            invalid_records=invalid_count,
            duplicate_records=len(duplicate_record_indexes),
            changed_field_count=changed_field_count,
            records=tuple(normalized_records),
            findings=tuple(findings),
        )

    def _normalize_path(self, value: str) -> tuple[str, str | None]:
        candidate = value.strip().replace("\\", "/")

        if not candidate:
            return "", "INVALID_PATH_FIELD"

        is_absolute = candidate.startswith("/") or bool(
            re.match(r"^[A-Za-z]:/", candidate)
        )

        if is_absolute and self._reject_absolute_paths:
            return "", "ABSOLUTE_PATH_NOT_ALLOWED"

        normalized = posixpath.normpath(candidate)

        if normalized == ".":
            return "", "INVALID_PATH_FIELD"

        if normalized == ".." or normalized.startswith("../"):
            return "", "PATH_TRAVERSAL_NOT_ALLOWED"

        if is_absolute:
            return normalized, None

        if normalized.startswith("/"):
            return "", "ABSOLUTE_PATH_NOT_ALLOWED"

        return normalized, None

    def _identifier_key(self, identifier: str) -> str:
        if self._case_insensitive_identifiers:
            return identifier.casefold()
        return identifier

    @staticmethod
    def _validate_field_collection(
        values: Iterable[str],
        field_name: str,
    ) -> tuple[str, ...]:
        if isinstance(values, (str, bytes)):
            raise IntelligenceDataIntegrityError(
                f"{field_name} must be an iterable of field names."
            )

        try:
            result = tuple(values)
        except TypeError as exc:
            raise IntelligenceDataIntegrityError(
                f"{field_name} must be iterable."
            ) from exc

        normalized: list[str] = []
        for value in result:
            if not isinstance(value, str) or not value.strip():
                raise IntelligenceDataIntegrityError(
                    f"{field_name} must contain only non-empty strings."
                )
            normalized.append(value.strip())

        if len(normalized) != len(set(normalized)):
            raise IntelligenceDataIntegrityError(
                f"{field_name} cannot contain duplicate field names."
            )

        return tuple(normalized)

    @staticmethod
    def _validate_field_name(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise IntelligenceDataIntegrityError(
                f"{field_name} must be a non-empty string."
            )
        return value.strip()

    @staticmethod
    def _validate_boolean(value: bool, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise IntelligenceDataIntegrityError(
                f"{field_name} must be a boolean."
            )
        return value