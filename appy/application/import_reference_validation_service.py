
"""Validate import module and imported-symbol references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from appy.application.import_analyzer import ImportRecord


class ImportReferenceValidationError(ValueError):
    """Raised when import/reference validation receives invalid input."""


class ImportReferenceSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ImportReferenceStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNRESOLVED = "unresolved"
    EXTERNAL = "external"


@dataclass(frozen=True)
class ImportReferenceIssue:
    """One import or symbol-reference validation finding."""

    code: str
    message: str
    source_file: str
    line: int
    severity: ImportReferenceSeverity
    status: ImportReferenceStatus
    imported_module: str | None = None
    imported_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be a non-empty string.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string.")
        if not isinstance(self.source_file, str) or not self.source_file.strip():
            raise ValueError("source_file must be a non-empty string.")
        if (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 1
        ):
            raise ValueError("line must be a positive integer.")
        if not isinstance(self.severity, ImportReferenceSeverity):
            raise TypeError("severity must be an ImportReferenceSeverity.")
        if not isinstance(self.status, ImportReferenceStatus):
            raise TypeError("status must be an ImportReferenceStatus.")
        if self.imported_module is not None and not isinstance(
            self.imported_module, str
        ):
            raise TypeError("imported_module must be a string or None.")
        if self.imported_name is not None and not isinstance(
            self.imported_name, str
        ):
            raise TypeError("imported_name must be a string or None.")


@dataclass(frozen=True)
class ImportReferenceRecord:
    """Validation result for one import record."""

    source_file: str
    line: int
    imported_module: str | None
    imported_name: str | None
    alias: str | None
    status: ImportReferenceStatus
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_file, str) or not self.source_file.strip():
            raise ValueError("source_file must be a non-empty string.")
        if (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 1
        ):
            raise ValueError("line must be a positive integer.")
        if not isinstance(self.status, ImportReferenceStatus):
            raise TypeError("status must be an ImportReferenceStatus.")
        if not isinstance(self.message, str):
            raise TypeError("message must be a string.")


@dataclass(frozen=True)
class ImportReferenceValidationResult:
    """Repository-wide import/reference validation result."""

    total_imports: int
    valid_imports: int
    invalid_imports: int
    unresolved_imports: int
    external_imports: int
    records: tuple[ImportReferenceRecord, ...]
    issues: tuple[ImportReferenceIssue, ...]

    def __post_init__(self) -> None:
        for name in (
            "total_imports",
            "valid_imports",
            "invalid_imports",
            "unresolved_imports",
            "external_imports",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        if (
            self.valid_imports
            + self.invalid_imports
            + self.unresolved_imports
            + self.external_imports
            != self.total_imports
        ):
            raise ValueError("Import status counts must equal total_imports.")

        if not isinstance(self.records, tuple):
            raise TypeError("records must be a tuple.")
        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple.")
        if not all(
            isinstance(record, ImportReferenceRecord)
            for record in self.records
        ):
            raise TypeError("records must contain ImportReferenceRecord objects.")
        if not all(
            isinstance(issue, ImportReferenceIssue)
            for issue in self.issues
        ):
            raise TypeError("issues must contain ImportReferenceIssue objects.")
        if len(self.records) != self.total_imports:
            raise ValueError("records length must match total_imports.")

    @property
    def is_valid(self) -> bool:
        return self.invalid_imports == 0

    @property
    def has_unresolved_imports(self) -> bool:
        return self.unresolved_imports > 0

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity == ImportReferenceSeverity.ERROR
            for issue in self.issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity == ImportReferenceSeverity.WARNING
            for issue in self.issues
        )

    @property
    def healthy(self) -> bool:
        return self.is_valid


class ImportReferenceValidationService:
    """Validate imports using a repository module and symbol inventory.

    `internal_modules` contains importable module names, such as
    "appy.services.user_service" or paths such as "appy/services/user_service.py".

    `module_exports` optionally maps module names to known exported symbols.
    If a module is known but its exported-symbol inventory is not supplied,
    imported names cannot be conclusively verified and are treated as valid
    module references rather than guessed to be invalid.
    """

    def validate(
        self,
        imports: Iterable[ImportRecord],
        internal_modules: Iterable[str],
        module_exports: Mapping[str, Iterable[str]] | None = None,
    ) -> ImportReferenceValidationResult:
        import_records = self._materialize_imports(imports)
        known_modules = self._materialize_modules(internal_modules)
        exports = self._materialize_exports(module_exports)

        normalized_modules = {
            self._normalize_module(module): module
            for module in known_modules
        }

        normalized_exports = {
            self._normalize_module(module): symbols
            for module, symbols in exports.items()
        }

        records: list[ImportReferenceRecord] = []
        issues: list[ImportReferenceIssue] = []

        counts = {
            ImportReferenceStatus.VALID: 0,
            ImportReferenceStatus.INVALID: 0,
            ImportReferenceStatus.UNRESOLVED: 0,
            ImportReferenceStatus.EXTERNAL: 0,
        }

        for record in import_records:
            status, code, message, severity = self._validate_one(
                record,
                normalized_modules,
                normalized_exports,
            )

            counts[status] += 1

            records.append(
                ImportReferenceRecord(
                    source_file=record.filename,
                    line=record.line,
                    imported_module=record.module,
                    imported_name=record.imported_name,
                    alias=record.alias,
                    status=status,
                    message=message,
                )
            )

            if status != ImportReferenceStatus.VALID:
                issues.append(
                    ImportReferenceIssue(
                        code=code,
                        message=message,
                        source_file=record.filename,
                        line=record.line,
                        severity=severity,
                        status=status,
                        imported_module=record.module,
                        imported_name=record.imported_name,
                    )
                )

        return ImportReferenceValidationResult(
            total_imports=len(import_records),
            valid_imports=counts[ImportReferenceStatus.VALID],
            invalid_imports=counts[ImportReferenceStatus.INVALID],
            unresolved_imports=counts[ImportReferenceStatus.UNRESOLVED],
            external_imports=counts[ImportReferenceStatus.EXTERNAL],
            records=tuple(records),
            issues=tuple(
                sorted(
                    issues,
                    key=lambda issue: (
                        issue.source_file,
                        issue.line,
                        issue.code,
                        issue.message,
                    ),
                )
            ),
        )

    def _validate_one(
        self,
        record: ImportRecord,
        known_modules: Mapping[str, str],
        module_exports: Mapping[str, set[str]],
    ) -> tuple[
        ImportReferenceStatus,
        str,
        str,
        ImportReferenceSeverity,
    ]:
        if record.is_relative:
            return (
                ImportReferenceStatus.UNRESOLVED,
                "RELATIVE_IMPORT_UNRESOLVED",
                "Relative import cannot be resolved without package context.",
                ImportReferenceSeverity.WARNING,
            )

        module = record.module

        if not module:
            return (
                ImportReferenceStatus.UNRESOLVED,
                "MISSING_IMPORT_MODULE",
                "Import record does not contain a module name.",
                ImportReferenceSeverity.WARNING,
            )

        normalized = self._normalize_module(module)

        if not normalized:
            return (
                ImportReferenceStatus.INVALID,
                "INVALID_IMPORT_MODULE",
                "Import module name is invalid.",
                ImportReferenceSeverity.ERROR,
            )

        resolved_module = self._resolve_module(normalized, known_modules)

        if resolved_module is None:
            # A module not found in the repository inventory may be an
            # installed third-party package or a standard-library module.
            return (
                ImportReferenceStatus.EXTERNAL,
                "MODULE_NOT_IN_REPOSITORY",
                "Module is not present in the supplied repository module inventory.",
                ImportReferenceSeverity.WARNING,
            )

        if record.import_type == "from_import" and record.imported_name:
            symbols = module_exports.get(resolved_module)

            if symbols is not None and record.imported_name not in symbols:
                return (
                    ImportReferenceStatus.INVALID,
                    "IMPORTED_SYMBOL_NOT_FOUND",
                    (
                        f"Module '{module}' does not declare imported name "
                        f"'{record.imported_name}' in the supplied export inventory."
                    ),
                    ImportReferenceSeverity.ERROR,
                )

        return (
            ImportReferenceStatus.VALID,
            "",
            "Import reference is present in the repository module inventory.",
            ImportReferenceSeverity.WARNING,
        )

    @staticmethod
    def _resolve_module(
        requested: str,
        known_modules: Mapping[str, str],
    ) -> str | None:
        """Resolve a module or package against the known module inventory."""
        if requested in known_modules:
            return requested

        # A package can be represented by a known child module.
        if any(name.startswith(requested + ".") for name in known_modules):
            return requested

        # Importing a package may be satisfied by its __init__.py module.
        package_init = requested + ".__init__"
        if package_init in known_modules:
            return package_init

        return None

    @staticmethod
    def _normalize_module(module: str) -> str:
        normalized = module.strip().replace("\\", "/")

        if normalized.endswith(".py"):
            normalized = normalized[:-3]

        normalized = normalized.replace("/", ".")
        normalized = re.sub(r"\.+", ".", normalized).strip(".")

        return normalized

    @classmethod
    def _materialize_imports(
        cls,
        imports: Iterable[ImportRecord],
    ) -> tuple[ImportRecord, ...]:
        if imports is None or isinstance(
            imports,
            (str, bytes, dict, set, frozenset),
        ):
            raise ImportReferenceValidationError(
                "imports must be an iterable of ImportRecord objects."
            )

        try:
            records = tuple(imports)
        except TypeError as exc:
            raise ImportReferenceValidationError(
                "imports must be iterable."
            ) from exc

        if not all(isinstance(record, ImportRecord) for record in records):
            raise ImportReferenceValidationError(
                "Every import must be an ImportRecord."
            )

        for record in records:
            if not isinstance(record.filename, str) or not record.filename.strip():
                raise ImportReferenceValidationError(
                    "Import filename must be a non-empty string."
                )
            if (
                isinstance(record.line, bool)
                or not isinstance(record.line, int)
                or record.line < 1
            ):
                raise ImportReferenceValidationError(
                    "Import line must be a positive integer."
                )
            if (
                isinstance(record.level, bool)
                or not isinstance(record.level, int)
                or record.level < 0
            ):
                raise ImportReferenceValidationError(
                    "Import level must be a non-negative integer."
                )
            if record.import_type not in {"import", "from_import"}:
                raise ImportReferenceValidationError(
                    "Import type must be 'import' or 'from_import'."
                )
            if record.module is not None and not isinstance(record.module, str):
                raise ImportReferenceValidationError(
                    "Import module must be a string or None."
                )
            if (
                record.imported_name is not None
                and not isinstance(record.imported_name, str)
            ):
                raise ImportReferenceValidationError(
                    "Imported name must be a string or None."
                )
            if record.alias is not None and not isinstance(record.alias, str):
                raise ImportReferenceValidationError(
                    "Import alias must be a string or None."
                )

        return records

    @classmethod
    def _materialize_modules(
        cls,
        internal_modules: Iterable[str],
    ) -> tuple[str, ...]:
        if internal_modules is None or isinstance(
            internal_modules,
            (str, bytes, dict, set, frozenset),
        ):
            raise ImportReferenceValidationError(
                "internal_modules must be an iterable of module names."
            )

        try:
            modules = tuple(internal_modules)
        except TypeError as exc:
            raise ImportReferenceValidationError(
                "internal_modules must be iterable."
            ) from exc

        for module in modules:
            if not isinstance(module, str) or not module.strip():
                raise ImportReferenceValidationError(
                    "Every internal module must be a non-empty string."
                )

            normalized = cls._normalize_module(module)
            if not normalized:
                raise ImportReferenceValidationError(
                    f"Invalid internal module name: {module!r}."
                )

        return modules

    @classmethod
    def _materialize_exports(
        cls,
        module_exports: Mapping[str, Iterable[str]] | None,
    ) -> dict[str, set[str]]:
        if module_exports is None:
            return {}

        if not isinstance(module_exports, Mapping):
            raise ImportReferenceValidationError(
                "module_exports must be a mapping of module names to symbols."
            )

        result: dict[str, set[str]] = {}

        for module, symbols in module_exports.items():
            if not isinstance(module, str) or not module.strip():
                raise ImportReferenceValidationError(
                    "Export module names must be non-empty strings."
                )

            if symbols is None or isinstance(
                symbols,
                (str, bytes, dict, set, frozenset),
            ):
                raise ImportReferenceValidationError(
                    "Each module export collection must be an iterable of symbol names."
                )

            try:
                symbol_values = tuple(symbols)
            except TypeError as exc:
                raise ImportReferenceValidationError(
                    "Module exports must be iterable."
                ) from exc

            if not all(
                isinstance(symbol, str) and symbol.strip()
                for symbol in symbol_values
            ):
                raise ImportReferenceValidationError(
                    "Exported symbol names must be non-empty strings."
                )

            normalized_module = cls._normalize_module(module)
            if not normalized_module:
                raise ImportReferenceValidationError(
                    f"Invalid export module name: {module!r}."
                )

            if normalized_module in result:
                raise ImportReferenceValidationError(
                    f"Duplicate normalized export module: {module!r}."
                )

            result[normalized_module] = set(symbol_values)

        return result
