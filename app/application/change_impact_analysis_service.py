
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from app.application.call_graph_service import (
    CallGraphResult,
)
from app.application.code_entity_extractor import CodeEntity
from app.application.dependency_analyzer import DependencyRecord


class ChangeImpactAnalysisError(ValueError):
    """Raised when change impact analysis receives invalid input."""


@dataclass(frozen=True)
class ChangeImpactTarget:
    """Represents a file or code entity selected for change."""

    target_type: str
    value: str

    def __post_init__(self):
        if self.target_type not in {"file", "entity"}:
            raise ChangeImpactAnalysisError(
                "Target type must be 'file' or 'entity'."
            )

        if not isinstance(self.value, str) or not self.value.strip():
            raise ChangeImpactAnalysisError(
                "Target value must be a non-empty string."
            )

        normalized = self.value.strip()

        if self.target_type == "file":
            normalized = _normalize_file_path(normalized)

        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class ChangeImpactFinding:
    """Represents one repository element potentially affected by a change."""

    source_file: str
    affected_file: str
    relationship_type: str
    changed_target: str
    affected_entity: str
    line: int
    reason: str

    def __post_init__(self):
        for field_name in (
            "source_file",
            "affected_file",
            "relationship_type",
            "changed_target",
            "affected_entity",
            "reason",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ChangeImpactAnalysisError(
                    f"{field_name} must be a non-empty string."
                )

        if (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 0
        ):
            raise ChangeImpactAnalysisError(
                "Line must be a non-negative integer."
            )


@dataclass(frozen=True)
class ChangeImpactAnalysisResult:
    """Contains the immediate impact candidates for requested changes."""

    changed_targets: tuple
    total_files_analyzed: int
    total_entities_analyzed: int
    total_calls_analyzed: int
    total_dependencies_analyzed: int
    total_impact_findings: int
    affected_files: tuple
    findings: tuple

    def __post_init__(self):
        tuple_fields = (
            "changed_targets",
            "affected_files",
            "findings",
        )

        for field_name in tuple_fields:
            if not isinstance(getattr(self, field_name), tuple):
                raise ChangeImpactAnalysisError(
                    f"{field_name} must be a tuple."
                )

        for field_name in (
            "total_files_analyzed",
            "total_entities_analyzed",
            "total_calls_analyzed",
            "total_dependencies_analyzed",
            "total_impact_findings",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ChangeImpactAnalysisError(
                    f"{field_name} must be a non-negative integer."
                )

        if self.total_impact_findings != len(self.findings):
            raise ChangeImpactAnalysisError(
                "Total impact findings must match the findings count."
            )

        if not all(
            isinstance(target, ChangeImpactTarget)
            for target in self.changed_targets
        ):
            raise ChangeImpactAnalysisError(
                "Changed targets must contain ChangeImpactTarget objects."
            )

        if not all(
            isinstance(finding, ChangeImpactFinding)
            for finding in self.findings
        ):
            raise ChangeImpactAnalysisError(
                "Findings must contain ChangeImpactFinding objects."
            )

        if not all(
            isinstance(path, str) and path.strip()
            for path in self.affected_files
        ):
            raise ChangeImpactAnalysisError(
                "Affected files must contain non-empty strings."
            )

    @property
    def has_impact(self) -> bool:
        return bool(self.findings)

    @property
    def healthy(self) -> bool:
        """True when analysis completed without identifying impact candidates."""
        return not self.findings

    @property
    def affected_file_count(self) -> int:
        return len(self.affected_files)

    @property
    def findings_by_relationship(self) -> dict:
        counts = {}
        for finding in self.findings:
            counts[finding.relationship_type] = (
                counts.get(finding.relationship_type, 0) + 1
            )
        return counts


def _normalize_file_path(value: str) -> str:
    """Normalize a repository-relative file path safely."""
    if not isinstance(value, str) or not value.strip():
        raise ChangeImpactAnalysisError(
            "File paths must be non-empty strings."
        )

    normalized = value.strip().replace("\\", "/")

    if normalized.startswith("/") or (
        len(normalized) >= 2 and normalized[1] == ":"
    ):
        raise ChangeImpactAnalysisError(
            "File paths must be repository-relative."
        )

    parts = normalized.split("/")

    if any(part in {"", ".", ".."} for part in parts):
        raise ChangeImpactAnalysisError(
            "File path contains an invalid path segment."
        )

    return str(PurePosixPath(*parts))


class ChangeImpactAnalysisService:
    """Identify immediate change-impact candidates from repository evidence.

    This service uses existing call graph, code entity, and dependency
    analysis results. It does not perform transitive impact traversal;
    that responsibility belongs to the Direct & Indirect Impact
    Detection Service.
    """

    RELATIONSHIP_FUNCTION_CALL = "function_call"
    RELATIONSHIP_METHOD_CALL = "method_call"
    RELATIONSHIP_IMPORT = "import"

    def analyze(
        self,
        changed_files: Iterable[str] = (),
        changed_entities: Iterable[str] = (),
        code_entities: Iterable[CodeEntity] = (),
        call_graphs: Iterable[CallGraphResult] = (),
        dependencies: Iterable[DependencyRecord] = (),
    ) -> ChangeImpactAnalysisResult:
        """Analyze immediate references to changed files and entities."""
        file_targets = self._materialize_strings(
            changed_files,
            "changed_files",
            normalize_paths=True,
        )
        entity_targets = self._materialize_strings(
            changed_entities,
            "changed_entities",
        )
        entities = self._materialize_records(
            code_entities,
            CodeEntity,
            "code_entities",
        )
        graphs = self._materialize_records(
            call_graphs,
            CallGraphResult,
            "call_graphs",
        )
        dependency_records = self._materialize_records(
            dependencies,
            DependencyRecord,
            "dependencies",
        )

        targets = tuple(
            sorted(
                {
                    ChangeImpactTarget("file", value)
                    for value in file_targets
                }
                | {
                    ChangeImpactTarget("entity", value)
                    for value in entity_targets
                },
                key=lambda item: (item.target_type, item.value),
            )
        )

        if not targets:
            raise ChangeImpactAnalysisError(
                "At least one changed file or entity must be provided."
            )

        changed_file_set = set(file_targets)
        changed_entity_set = set(entity_targets)

        entity_file_map = self._build_entity_file_map(entities)
        changed_modules = {
            self._module_name(path) for path in changed_file_set
        }

        changed_entity_names = set(changed_entity_set)

        for entity in entities:
            if entity.filename in changed_file_set:
                changed_entity_names.add(entity.qualified_name)

        findings = []

        findings.extend(
            self._analyze_calls(
                graphs,
                changed_file_set,
                changed_entity_names,
                entity_file_map,
            )
        )

        findings.extend(
            self._analyze_dependencies(
                dependency_records,
                changed_file_set,
                changed_modules,
                changed_entity_set,
            )
        )

        unique_findings = {
            (
                item.source_file,
                item.affected_file,
                item.relationship_type,
                item.changed_target,
                item.affected_entity,
                item.line,
                item.reason,
            ): item
            for item in findings
        }

        ordered_findings = tuple(
            sorted(
                unique_findings.values(),
                key=lambda item: (
                    item.affected_file,
                    item.line,
                    item.relationship_type,
                    item.changed_target,
                    item.affected_entity,
                ),
            )
        )

        affected_files = tuple(
            sorted({item.affected_file for item in ordered_findings})
        )

        analyzed_files = {
            _normalize_file_path(graph.filename)
            for graph in graphs
        }
        analyzed_files.update(
            _normalize_file_path(entity.filename)
            for entity in entities
        )
        analyzed_files.update(
            _normalize_file_path(record.source_file)
            for record in dependency_records
        )

        return ChangeImpactAnalysisResult(
            changed_targets=targets,
            total_files_analyzed=len(analyzed_files),
            total_entities_analyzed=len(entities),
            total_calls_analyzed=sum(
                graph.total_calls for graph in graphs
            ),
            total_dependencies_analyzed=len(dependency_records),
            total_impact_findings=len(ordered_findings),
            affected_files=affected_files,
            findings=ordered_findings,
        )

    @staticmethod
    def _materialize_strings(values, name, normalize_paths=False):
        if values is None or isinstance(
            values, (str, bytes, dict, set, frozenset)
        ):
            raise ChangeImpactAnalysisError(
                f"{name} must be an ordered iterable of strings."
            )

        try:
            materialized = tuple(values)
        except TypeError as exc:
            raise ChangeImpactAnalysisError(
                f"{name} must be iterable."
            ) from exc

        normalized = []

        for value in materialized:
            if not isinstance(value, str) or not value.strip():
                raise ChangeImpactAnalysisError(
                    f"Every value in {name} must be a non-empty string."
                )

            if normalize_paths:
                normalized.append(_normalize_file_path(value))
            else:
                normalized.append(value.strip())

        return tuple(dict.fromkeys(normalized))

    @staticmethod
    def _materialize_records(values, expected_type, name):
        if values is None or isinstance(
            values, (str, bytes, dict, set, frozenset)
        ):
            raise ChangeImpactAnalysisError(
                f"{name} must be an ordered iterable."
            )

        try:
            materialized = tuple(values)
        except TypeError as exc:
            raise ChangeImpactAnalysisError(
                f"{name} must be iterable."
            ) from exc

        if not all(
            isinstance(value, expected_type) for value in materialized
        ):
            raise ChangeImpactAnalysisError(
                f"Every item in {name} must be a "
                f"{expected_type.__name__} instance."
            )

        return materialized

    @staticmethod
    def _build_entity_file_map(entities):
        result = {}

        for entity in entities:
            result.setdefault(entity.qualified_name, set()).add(
                _normalize_file_path(entity.filename)
            )

        return result

    def _analyze_calls(
        self,
        call_graphs,
        changed_files,
        changed_entities,
        entity_file_map,
    ):
        findings = []

        for graph in call_graphs:
            graph_file = _normalize_file_path(graph.filename)

            for call in graph.calls:
                caller_file = _normalize_file_path(call.filename)

                if caller_file in changed_files:
                    continue

                matching_targets = self._matching_entity_targets(
                    call.callee,
                    changed_entities,
                )

                for changed_target in matching_targets:
                    target_files = entity_file_map.get(
                        changed_target,
                        set(),
                    )

                    if target_files and caller_file not in target_files:
                        relationship = (
                            self.RELATIONSHIP_METHOD_CALL
                            if call.caller_type == "method"
                            else self.RELATIONSHIP_FUNCTION_CALL
                        )

                        findings.append(
                            ChangeImpactFinding(
                                source_file=caller_file,
                                affected_file=caller_file,
                                relationship_type=relationship,
                                changed_target=changed_target,
                                affected_entity=call.caller,
                                line=call.line,
                                reason=(
                                    f"{call.caller} calls changed entity "
                                    f"{changed_target}."
                                ),
                            )
                        )

        return findings

    @staticmethod
    def _matching_entity_targets(callee, changed_entities):
        matches = []

        for target in changed_entities:
            simple_name = target.rsplit(".", 1)[-1]

            if callee == target or callee == simple_name:
                matches.append(target)
            elif callee.endswith("." + target):
                matches.append(target)

        return tuple(sorted(set(matches)))

    def _analyze_dependencies(
        self,
        dependencies,
        changed_files,
        changed_modules,
        changed_entities,
    ):
        findings = []

        for dependency in dependencies:
            source_file = _normalize_file_path(
                dependency.source_file
            )

            if source_file in changed_files:
                continue

            imported_module = dependency.imported_module
            if not imported_module:
                continue

            normalized_module = self._normalize_module(imported_module)

            matching_file_targets = [
                path
                for path in changed_files
                if self._module_name(path) == normalized_module
                or normalized_module.startswith(
                    self._module_name(path) + "."
                )
            ]

            for changed_file in matching_file_targets:
                findings.append(
                    ChangeImpactFinding(
                        source_file=source_file,
                        affected_file=source_file,
                        relationship_type=self.RELATIONSHIP_IMPORT,
                        changed_target=changed_file,
                        affected_entity=(
                            dependency.imported_name
                            or imported_module
                        ),
                        line=dependency.line,
                        reason=(
                            f"{source_file} imports changed module "
                            f"{normalized_module}."
                        ),
                    )
                )

            if dependency.imported_name:
                for changed_entity in changed_entities:
                    if (
                        dependency.imported_name == changed_entity
                        or dependency.imported_name
                        == changed_entity.rsplit(".", 1)[-1]
                    ):
                        findings.append(
                            ChangeImpactFinding(
                                source_file=source_file,
                                affected_file=source_file,
                                relationship_type=self.RELATIONSHIP_IMPORT,
                                changed_target=changed_entity,
                                affected_entity=dependency.imported_name,
                                line=dependency.line,
                                reason=(
                                    f"{source_file} imports changed "
                                    f"entity {changed_entity}."
                                ),
                            )
                        )

        return findings

    @staticmethod
    def _module_name(file_path):
        path = PurePosixPath(file_path)

        if path.name == "__init__.py":
            return ".".join(path.parts[:-1])

        if path.suffix == ".py":
            return ".".join(path.with_suffix("").parts)

        return path.stem

    @staticmethod
    def _normalize_module(module):
        normalized = module.strip().replace("\\", "/")

        if normalized.endswith(".py"):
            normalized = normalized[:-3]

        return normalized.replace("/", ".").strip(".")
