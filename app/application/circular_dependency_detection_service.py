
"""Detect circular dependencies between internal repository modules."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.application.dependency_analyzer import DependencyRecord


class CircularDependencyDetectionError(ValueError):
    """Raised when circular dependency analysis receives invalid input."""


@dataclass(frozen=True)
class CircularDependency:
    """A directed circular dependency chain."""

    cycle_id: str
    modules: tuple[str, ...]
    dependency_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.cycle_id, str) or not self.cycle_id:
            raise CircularDependencyDetectionError(
                "cycle_id must be a non-empty string."
            )
        if not isinstance(self.modules, tuple) or len(self.modules) < 2:
            raise CircularDependencyDetectionError(
                "modules must be a tuple containing a cycle."
            )
        if any(not isinstance(item, str) or not item for item in self.modules):
            raise CircularDependencyDetectionError(
                "Every module in a cycle must be a non-empty string."
            )
        if self.modules[0] != self.modules[-1]:
            raise CircularDependencyDetectionError(
                "A cycle must begin and end with the same module."
            )
        if len(set(self.modules[:-1])) != len(self.modules) - 1:
            raise CircularDependencyDetectionError(
                "A cycle cannot repeat an intermediate module."
            )
        if (
            isinstance(self.dependency_count, bool)
            or not isinstance(self.dependency_count, int)
            or self.dependency_count != len(self.modules) - 1
        ):
            raise CircularDependencyDetectionError(
                "dependency_count must equal the number of cycle edges."
            )


@dataclass(frozen=True)
class CircularDependencyDetectionResult:
    """Summary of circular dependency analysis."""

    total_dependencies: int
    dependencies_checked: int
    internal_dependencies: int
    ignored_dependencies: int
    total_modules: int
    cycle_count: int
    cycles: tuple[CircularDependency, ...]

    def __post_init__(self) -> None:
        numeric_fields = (
            self.total_dependencies,
            self.dependencies_checked,
            self.internal_dependencies,
            self.ignored_dependencies,
            self.total_modules,
            self.cycle_count,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in numeric_fields
        ):
            raise CircularDependencyDetectionError(
                "Result counts must be non-negative integers."
            )
        if self.dependencies_checked != self.total_dependencies:
            raise CircularDependencyDetectionError(
                "dependencies_checked must equal total_dependencies."
            )
        if self.internal_dependencies + self.ignored_dependencies != (
            self.total_dependencies
        ):
            raise CircularDependencyDetectionError(
                "Internal and ignored dependency counts must equal total."
            )
        if not isinstance(self.cycles, tuple):
            raise CircularDependencyDetectionError("cycles must be a tuple.")
        if self.cycle_count != len(self.cycles):
            raise CircularDependencyDetectionError(
                "cycle_count must equal the number of cycles."
            )
        if any(not isinstance(cycle, CircularDependency) for cycle in self.cycles):
            raise CircularDependencyDetectionError(
                "Every cycle must be a CircularDependency."
            )

    @property
    def has_cycles(self) -> bool:
        return self.cycle_count > 0

    @property
    def healthy(self) -> bool:
        return not self.has_cycles

    @property
    def modules_in_cycles(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    module
                    for cycle in self.cycles
                    for module in cycle.modules[:-1]
                }
            )
        )


class CircularDependencyDetectionService:
    """Detect directed cycles in internal module dependency relationships."""

    INTERNAL = "internal"

    def analyze(
        self,
        dependencies: Iterable[DependencyRecord],
        internal_modules: Iterable[str] = (),
        module_to_file: Mapping[str, str] | None = None,
    ) -> CircularDependencyDetectionResult:
        records = self._materialize_dependencies(dependencies)
        inventory = self._materialize_internal_modules(internal_modules)
        mapping = self._validate_module_to_file(module_to_file)

        module_aliases = self._build_module_aliases(inventory, mapping)

        internal_records = [
            record
            for record in records
            if record.dependency_type == self.INTERNAL
        ]
        ignored_count = len(records) - len(internal_records)

        if not inventory:
            inferred: set[str] = set()
            for record in internal_records:
                source = self._source_module(record.source_file)
                target = self._normalize_module(record.imported_module)
                if source:
                    inferred.add(source)
                if target:
                    inferred.add(target)
            module_aliases = {module: module for module in inferred}

        graph: dict[str, set[str]] = {
            module: set() for module in module_aliases.values()
        }

        for record in internal_records:
            source_module = self._resolve_source_module(
                record.source_file, module_aliases, mapping
            )
            target_module = self._resolve_target_module(
                record.imported_module, module_aliases
            )

            if source_module is None or target_module is None:
                continue

            graph.setdefault(source_module, set()).add(target_module)
            graph.setdefault(target_module, set())

        cycles = self._find_cycles(graph)
        cycle_models = tuple(self._create_cycle(cycle) for cycle in cycles)

        return CircularDependencyDetectionResult(
            total_dependencies=len(records),
            dependencies_checked=len(records),
            internal_dependencies=len(internal_records),
            ignored_dependencies=ignored_count,
            total_modules=len(graph),
            cycle_count=len(cycle_models),
            cycles=cycle_models,
        )

    @staticmethod
    def _materialize_dependencies(
        dependencies: Iterable[DependencyRecord],
    ) -> tuple[DependencyRecord, ...]:
        if isinstance(dependencies, (str, bytes, set, frozenset, Mapping)):
            raise CircularDependencyDetectionError(
                "dependencies must be an ordered iterable of DependencyRecord objects."
            )
        try:
            records = tuple(dependencies)
        except TypeError as exc:
            raise CircularDependencyDetectionError(
                "dependencies must be iterable."
            ) from exc

        if any(not isinstance(item, DependencyRecord) for item in records):
            raise CircularDependencyDetectionError(
                "Every dependency must be a DependencyRecord."
            )
        return records

    @classmethod
    def _materialize_internal_modules(
        cls, internal_modules: Iterable[str]
    ) -> tuple[str, ...]:
        if isinstance(internal_modules, (str, bytes, set, frozenset, Mapping)):
            raise CircularDependencyDetectionError(
                "internal_modules must be an ordered iterable of module names or paths."
            )
        try:
            values = tuple(internal_modules)
        except TypeError as exc:
            raise CircularDependencyDetectionError(
                "internal_modules must be iterable."
            ) from exc

        normalized: list[str] = []
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise CircularDependencyDetectionError(
                    "Every internal module must be a non-empty string."
                )
            module = cls._normalize_module(value)
            if not module:
                raise CircularDependencyDetectionError(
                    f"Invalid internal module: {value!r}."
                )
            normalized.append(module)

        if len(normalized) != len(set(normalized)):
            raise CircularDependencyDetectionError(
                "internal_modules cannot contain duplicate normalized modules."
            )
        return tuple(normalized)

    @classmethod
    def _validate_module_to_file(
        cls, module_to_file: Mapping[str, str] | None
    ) -> dict[str, str]:
        if module_to_file is None:
            return {}
        if not isinstance(module_to_file, Mapping):
            raise CircularDependencyDetectionError(
                "module_to_file must be a mapping."
            )

        result: dict[str, str] = {}
        for module, path in module_to_file.items():
            normalized_module = cls._normalize_module(module)
            if not normalized_module:
                raise CircularDependencyDetectionError(
                    f"Invalid module name in module_to_file: {module!r}."
                )
            if not isinstance(path, str) or not path.strip():
                raise CircularDependencyDetectionError(
                    "Every module_to_file value must be a non-empty path."
                )
            normalized_path = cls._normalize_path(path)
            if normalized_module in result:
                raise CircularDependencyDetectionError(
                    f"Duplicate normalized module mapping: {normalized_module}."
                )
            result[normalized_module] = normalized_path
        return result

    @classmethod
    def _build_module_aliases(
        cls,
        inventory: tuple[str, ...],
        module_to_file: Mapping[str, str],
    ) -> dict[str, str]:
        """Map recognized module names and source-path forms to canonical names."""
        aliases = {module: module for module in inventory}

        for module, path in module_to_file.items():
            aliases[module] = module
            path_module = cls._source_module(path)
            if path_module:
                existing = aliases.get(path_module)
                if existing is not None and existing != module:
                    raise CircularDependencyDetectionError(
                        f"Ambiguous module path alias: {path_module}."
                    )
                aliases[path_module] = module

        return aliases

    @staticmethod
    def _normalize_path(path: str) -> str:
        value = path.strip().replace("\\", "/")
        while value.startswith("./"):
            value = value[2:]
        return value

    @classmethod
    def _normalize_module(cls, value: str) -> str:
        """Normalize a module name or Python path without repairing bad syntax."""
        if not isinstance(value, str):
            return ""

        normalized = value.strip().replace("\\", "/")
        if not normalized:
            return ""

        while normalized.startswith("./"):
            normalized = normalized[2:]

        if normalized.endswith(".py"):
            normalized = normalized[:-3]

        if not normalized:
            return ""

        if "/" in normalized:
            parts = normalized.split("/")
        else:
            parts = normalized.split(".")

        if any(not part for part in parts):
            return ""

        if parts[-1] == "__init__":
            parts = parts[:-1]

        if not parts or any(not part.isidentifier() for part in parts):
            return ""

        return ".".join(parts)

    @classmethod
    def _source_module(cls, source_file: str) -> str:
        if not isinstance(source_file, str) or not source_file.strip():
            return ""
        return cls._normalize_module(cls._normalize_path(source_file))

    @classmethod
    def _resolve_source_module(
        cls,
        source_file: str,
        aliases: Mapping[str, str],
        module_to_file: Mapping[str, str],
    ) -> str | None:
        normalized_path = cls._normalize_path(source_file)
        for module, path in module_to_file.items():
            if normalized_path == path:
                return module

        source_module = cls._source_module(source_file)
        if source_module in aliases:
            return aliases[source_module]

        if source_module:
            candidates = [
                (alias, canonical)
                for alias, canonical in aliases.items()
                if source_module.endswith("." + alias)
                or alias.endswith("." + source_module)
            ]
            if candidates:
                candidates.sort(key=lambda item: (-len(item[0]), item[0]))
                return candidates[0][1]
        return None

    @classmethod
    def _resolve_target_module(
        cls, imported_module: str, aliases: Mapping[str, str]
    ) -> str | None:
        target = cls._normalize_module(imported_module)
        if not target:
            return None
        if target in aliases:
            return aliases[target]

        candidates = [
            (alias, canonical)
            for alias, canonical in aliases.items()
            if target.endswith("." + alias)
        ]
        if candidates:
            candidates.sort(key=lambda item: (-len(item[0]), item[0]))
            return candidates[0][1]
        return None

    @staticmethod
    def _find_cycles(
        graph: Mapping[str, set[str]]
    ) -> tuple[tuple[str, ...], ...]:
        """Find each simple directed cycle once, in canonical order."""
        found: set[tuple[str, ...]] = set()
        nodes = sorted(graph)

        for start in nodes:
            path = [start]
            visited = {start}

            def walk(current: str) -> None:
                for neighbor in sorted(graph.get(current, set())):
                    if neighbor == start:
                        found.add(tuple(path + [start]))
                    elif neighbor > start and neighbor not in visited:
                        visited.add(neighbor)
                        path.append(neighbor)
                        walk(neighbor)
                        path.pop()
                        visited.remove(neighbor)

            walk(start)

        return tuple(sorted(found))

    @staticmethod
    def _create_cycle(modules: tuple[str, ...]) -> CircularDependency:
        identity = "->".join(modules)
        cycle_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        return CircularDependency(
            cycle_id=cycle_id,
            modules=modules,
            dependency_count=len(modules) - 1,
        )
