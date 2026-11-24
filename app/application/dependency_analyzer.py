
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.application.import_analyzer import ImportRecord


class DependencyAnalyzerError(ValueError):
    """Raised when dependency analysis fails."""


@dataclass(frozen=True)
class DependencyRecord:
    """Represents a classified dependency."""

    source_file: str
    imported_module: str | None
    imported_name: str | None
    alias: str | None
    dependency_type: str
    line: int
    is_relative: bool


class DependencyAnalyzer:
    """Classify imports as internal, external, standard-library, or unresolved."""

    DEPENDENCY_INTERNAL = "internal"
    DEPENDENCY_EXTERNAL = "external"
    DEPENDENCY_STANDARD_LIBRARY = "standard_library"
    DEPENDENCY_UNRESOLVED = "unresolved"

    def __init__(self):
        self._stdlib_modules = getattr(
            sys,
            "stdlib_module_names",
            frozenset(),
        )

    def analyze(
        self,
        imports: Iterable[ImportRecord],
        internal_modules: Iterable[str] = (),
    ) -> tuple:
        """Classify import records using known repository modules."""

        if imports is None or isinstance(imports, (str, bytes, dict)):
            raise DependencyAnalyzerError(
                "Imports must be an iterable of ImportRecord objects."
            )

        if internal_modules is None or isinstance(
            internal_modules, (str, bytes, dict)
        ):
            raise DependencyAnalyzerError(
                "Internal modules must be an iterable of module names."
            )

        try:
            import_records = list(imports)
            known_modules = {
                self._normalize_module(module)
                for module in internal_modules
            }
        except TypeError as exc:
            raise DependencyAnalyzerError(
                "Invalid dependency analysis input."
            ) from exc

        if not all(
            isinstance(record, ImportRecord)
            for record in import_records
        ):
            raise DependencyAnalyzerError(
                "Every import must be an ImportRecord."
            )

        results = []

        for record in import_records:
            dependency_type = self._classify(
                record,
                known_modules,
            )

            results.append(
                DependencyRecord(
                    source_file=record.filename,
                    imported_module=record.module,
                    imported_name=record.imported_name,
                    alias=record.alias,
                    dependency_type=dependency_type,
                    line=record.line,
                    is_relative=record.is_relative,
                )
            )

        return tuple(results)

    def _classify(self, record, known_modules):
        """Determine the dependency category for one import."""

        module = record.module

        # Relative imports require package-context resolution.
        if record.is_relative or not module:
            return self.DEPENDENCY_UNRESOLVED

        normalized_module = self._normalize_module(module)

        if self._is_internal(normalized_module, known_modules):
            return self.DEPENDENCY_INTERNAL

        root_module = normalized_module.split(".", 1)[0]

        if root_module in self._stdlib_modules:
            return self.DEPENDENCY_STANDARD_LIBRARY

        return self.DEPENDENCY_EXTERNAL

    @staticmethod
    def _normalize_module(module: str) -> str:
        """Normalize module names and Python file paths."""

        if not isinstance(module, str) or not module.strip():
            raise DependencyAnalyzerError(
                "Module names must be non-empty strings."
            )

        normalized = module.strip().replace("\\", "/")

        if normalized.endswith(".py"):
            normalized = normalized[:-3]

        normalized = normalized.replace("/", ".")

        return normalized.strip(".")

    @staticmethod
    def _is_internal(module, known_modules):
        """Check whether a module belongs to the repository."""

        return any(
            module == known
            or module.startswith(known + ".")
            or known.startswith(module + ".")
            for known in known_modules
        )
