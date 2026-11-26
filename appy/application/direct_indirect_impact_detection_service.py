
from collections import deque
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from appy.application.call_graph_service import CallGraphResult
from appy.application.code_entity_extractor import CodeEntity
from appy.application.dependency_analyzer import DependencyRecord


class DirectIndirectImpactDetectionError(ValueError):
    """Raised when direct and indirect impact detection fails."""


@dataclass(frozen=True)
class ImpactPath:
    """Describes the relationship chain from a changed target to an impact."""

    nodes: tuple
    relationship_types: tuple

    def __post_init__(self):
        if not isinstance(self.nodes, tuple) or len(self.nodes) < 2:
            raise DirectIndirectImpactDetectionError(
                "An impact path must contain at least two nodes."
            )

        if not isinstance(self.relationship_types, tuple):
            raise DirectIndirectImpactDetectionError(
                "Relationship types must be a tuple."
            )

        if len(self.relationship_types) != len(self.nodes) - 1:
            raise DirectIndirectImpactDetectionError(
                "Each path edge must have one relationship type."
            )

        if not all(
            isinstance(node, str) and node.strip()
            for node in self.nodes
        ):
            raise DirectIndirectImpactDetectionError(
                "Path nodes must be non-empty strings."
            )

        if not all(
            isinstance(value, str) and value.strip()
            for value in self.relationship_types
        ):
            raise DirectIndirectImpactDetectionError(
                "Path relationship types must be non-empty strings."
            )

    @property
    def depth(self):
        return len(self.relationship_types)


@dataclass(frozen=True)
class DirectIndirectImpactFinding:
    """Represents a directly or indirectly affected repository component."""

    changed_target: str
    affected_file: str
    affected_entity: str
    impact_type: str
    depth: int
    relationship_types: tuple
    path: ImpactPath
    reason: str

    def __post_init__(self):
        for field_name in (
            "changed_target",
            "affected_file",
            "affected_entity",
            "impact_type",
            "reason",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DirectIndirectImpactDetectionError(
                    f"{field_name} must be a non-empty string."
                )

        if self.impact_type not in {"direct", "indirect"}:
            raise DirectIndirectImpactDetectionError(
                "Impact type must be 'direct' or 'indirect'."
            )

        if (
            isinstance(self.depth, bool)
            or not isinstance(self.depth, int)
            or self.depth < 1
        ):
            raise DirectIndirectImpactDetectionError(
                "Impact depth must be a positive integer."
            )

        if not isinstance(self.relationship_types, tuple):
            raise DirectIndirectImpactDetectionError(
                "Relationship types must be a tuple."
            )

        if not isinstance(self.path, ImpactPath):
            raise DirectIndirectImpactDetectionError(
                "Path must be an ImpactPath instance."
            )

        if self.depth != self.path.depth:
            raise DirectIndirectImpactDetectionError(
                "Finding depth must match its path depth."
            )

        if self.relationship_types != self.path.relationship_types:
            raise DirectIndirectImpactDetectionError(
                "Finding relationships must match its path."
            )


@dataclass(frozen=True)
class DirectIndirectImpactAnalysisResult:
    """Contains direct and indirect impact findings."""

    changed_targets: tuple
    total_graph_nodes: int
    total_relationships: int
    direct_impact_count: int
    indirect_impact_count: int
    total_impact_count: int
    affected_files: tuple
    findings: tuple
    maximum_impact_depth: int

    def __post_init__(self):
        for field_name in (
            "changed_targets",
            "affected_files",
            "findings",
        ):
            if not isinstance(getattr(self, field_name), tuple):
                raise DirectIndirectImpactDetectionError(
                    f"{field_name} must be a tuple."
                )

        for field_name in (
            "total_graph_nodes",
            "total_relationships",
            "direct_impact_count",
            "indirect_impact_count",
            "total_impact_count",
            "maximum_impact_depth",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise DirectIndirectImpactDetectionError(
                    f"{field_name} must be a non-negative integer."
                )

        if self.total_impact_count != len(self.findings):
            raise DirectIndirectImpactDetectionError(
                "Total impact count must match findings."
            )

        actual_direct = sum(
            finding.impact_type == "direct"
            for finding in self.findings
        )
        actual_indirect = sum(
            finding.impact_type == "indirect"
            for finding in self.findings
        )

        if self.direct_impact_count != actual_direct:
            raise DirectIndirectImpactDetectionError(
                "Direct impact count does not match findings."
            )

        if self.indirect_impact_count != actual_indirect:
            raise DirectIndirectImpactDetectionError(
                "Indirect impact count does not match findings."
            )

        if (
            self.direct_impact_count + self.indirect_impact_count
            != self.total_impact_count
        ):
            raise DirectIndirectImpactDetectionError(
                "Direct and indirect counts must equal total impact count."
            )

        if not all(
            isinstance(item, DirectIndirectImpactFinding)
            for item in self.findings
        ):
            raise DirectIndirectImpactDetectionError(
                "Findings must contain valid impact findings."
            )

        if not all(
            isinstance(path, str) and path.strip()
            for path in self.affected_files
        ):
            raise DirectIndirectImpactDetectionError(
                "Affected files must contain non-empty strings."
            )

        expected_files = tuple(
            sorted({item.affected_file for item in self.findings})
        )
        if self.affected_files != expected_files:
            raise DirectIndirectImpactDetectionError(
                "Affected files must match the finding records."
            )

        expected_depth = max(
            (item.depth for item in self.findings),
            default=0,
        )
        if self.maximum_impact_depth != expected_depth:
            raise DirectIndirectImpactDetectionError(
                "Maximum impact depth does not match findings."
            )

    @property
    def has_impact(self):
        return bool(self.findings)

    @property
    def has_direct_impact(self):
        return self.direct_impact_count > 0

    @property
    def has_indirect_impact(self):
        return self.indirect_impact_count > 0

    @property
    def healthy(self):
        return not self.has_impact

    @property
    def direct_findings(self):
        return tuple(
            item for item in self.findings
            if item.impact_type == "direct"
        )

    @property
    def indirect_findings(self):
        return tuple(
            item for item in self.findings
            if item.impact_type == "indirect"
        )


class DirectIndirectImpactDetectionService:
    """Trace direct and indirect impacts through repository relationships.

    Graph edges are represented as dependent -> dependency. Traversal
    starts at changed nodes and follows reverse edges to find dependents.

    Supported relationships:
    - Function and method calls from CallGraphResult.
    - Internal imports from DependencyRecord.
    - File ownership links connecting code entities to their files.

    File ownership links are traversal-only links. They do not create
    separate impact findings or increase impact depth.
    """

    CALL_RELATIONSHIP = "function_call"
    METHOD_RELATIONSHIP = "method_call"
    IMPORT_RELATIONSHIP = "import"
    CONTAINS_RELATIONSHIP = "contains"

    def analyze(
        self,
        changed_files: Iterable[str] = (),
        changed_entities: Iterable[str] = (),
        code_entities: Iterable[CodeEntity] = (),
        call_graphs: Iterable[CallGraphResult] = (),
        dependencies: Iterable[DependencyRecord] = (),
        max_depth: int = 10,
    ) -> DirectIndirectImpactAnalysisResult:
        """Identify direct and indirect impact paths."""
        self._validate_max_depth(max_depth)

        files = self._materialize_strings(
            changed_files,
            "changed_files",
            normalize_paths=True,
        )
        entities_requested = self._materialize_strings(
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

        if not files and not entities_requested:
            raise DirectIndirectImpactDetectionError(
                "At least one changed file or entity is required."
            )

        entity_map = self._build_entity_map(entities)
        file_nodes = self._build_file_nodes(
            files,
            entities,
            graphs,
            dependency_records,
        )

        changed_nodes = set(files)
        changed_nodes.update(
            self._module_name(path) for path in files
        )
        changed_nodes.update(entities_requested)

        for entity in entities:
            entity_file = _normalize_file_path(entity.filename)
            if entity_file in files:
                changed_nodes.add(entity.qualified_name)

        adjacency = {}
        all_nodes = set(changed_nodes)

        self._add_call_edges(
            adjacency,
            all_nodes,
            graphs,
            entity_map,
        )

        self._add_file_entity_edges(
            adjacency,
            all_nodes,
            entities,
        )

        self._add_import_edges(
            adjacency,
            all_nodes,
            dependency_records,
            file_nodes,
        )

        reverse_adjacency = self._reverse_edges(adjacency)

        findings = self._trace_impacts(
            changed_nodes,
            reverse_adjacency,
            entity_map,
            max_depth,
        )

        ordered_findings = tuple(
            sorted(
                findings,
                key=lambda item: (
                    item.depth,
                    item.affected_file,
                    item.affected_entity,
                    item.changed_target,
                    item.path.nodes,
                ),
            )
        )

        affected_files = tuple(
            sorted({item.affected_file for item in ordered_findings})
        )

        direct_count = sum(
            item.impact_type == "direct"
            for item in ordered_findings
        )
        indirect_count = len(ordered_findings) - direct_count

        return DirectIndirectImpactAnalysisResult(
            changed_targets=tuple(sorted(changed_nodes)),
            total_graph_nodes=len(all_nodes),
            total_relationships=sum(
                len(edges) for edges in adjacency.values()
            ),
            direct_impact_count=direct_count,
            indirect_impact_count=indirect_count,
            total_impact_count=len(ordered_findings),
            affected_files=affected_files,
            findings=ordered_findings,
            maximum_impact_depth=max(
                (item.depth for item in ordered_findings),
                default=0,
            ),
        )

    @staticmethod
    def _validate_max_depth(max_depth):
        if (
            isinstance(max_depth, bool)
            or not isinstance(max_depth, int)
            or max_depth < 1
        ):
            raise DirectIndirectImpactDetectionError(
                "max_depth must be a positive integer."
            )

    @staticmethod
    def _materialize_strings(values, name, normalize_paths=False):
        if values is None or isinstance(
            values, (str, bytes, dict, set, frozenset)
        ):
            raise DirectIndirectImpactDetectionError(
                f"{name} must be an ordered iterable of strings."
            )

        try:
            materialized = tuple(values)
        except TypeError as exc:
            raise DirectIndirectImpactDetectionError(
                f"{name} must be iterable."
            ) from exc

        result = []
        for value in materialized:
            if not isinstance(value, str) or not value.strip():
                raise DirectIndirectImpactDetectionError(
                    f"Every {name} value must be a non-empty string."
                )

            if normalize_paths:
                result.append(_normalize_file_path(value))
            else:
                result.append(value.strip())

        return tuple(dict.fromkeys(result))

    @staticmethod
    def _materialize_records(values, expected_type, name):
        if values is None or isinstance(
            values, (str, bytes, dict, set, frozenset)
        ):
            raise DirectIndirectImpactDetectionError(
                f"{name} must be an ordered iterable."
            )

        try:
            materialized = tuple(values)
        except TypeError as exc:
            raise DirectIndirectImpactDetectionError(
                f"{name} must be iterable."
            ) from exc

        if not all(
            isinstance(item, expected_type) for item in materialized
        ):
            raise DirectIndirectImpactDetectionError(
                f"Every item in {name} must be a "
                f"{expected_type.__name__} instance."
            )

        return materialized

    @staticmethod
    def _build_entity_map(entities):
        result = {}

        for entity in entities:
            result.setdefault(entity.qualified_name, []).append(entity)

        return {
            name: tuple(sorted(items, key=lambda item: item.filename))
            for name, items in result.items()
        }

    @staticmethod
    def _build_file_nodes(
        changed_files,
        entities,
        graphs,
        dependencies,
    ):
        nodes = set(changed_files)

        for entity in entities:
            nodes.add(_normalize_file_path(entity.filename))

        for graph in graphs:
            nodes.add(_normalize_file_path(graph.filename))

        for dependency in dependencies:
            nodes.add(_normalize_file_path(dependency.source_file))

        return nodes

    def _add_call_edges(
        self,
        adjacency,
        all_nodes,
        graphs,
        entity_map,
    ):
        for graph in graphs:
            for call in graph.calls:
                source_file = _normalize_file_path(call.filename)

                caller_node = self._resolve_caller_node(
                    source_file,
                    call.caller,
                    entity_map,
                )

                callee_nodes = self._resolve_callee_nodes(
                    call.callee,
                    entity_map,
                )

                for callee_node in callee_nodes:
                    if caller_node == callee_node:
                        continue

                    relationship = (
                        self.METHOD_RELATIONSHIP
                        if call.caller_type == "method"
                        else self.CALL_RELATIONSHIP
                    )

                    self._add_edge(
                        adjacency,
                        caller_node,
                        callee_node,
                        relationship,
                    )
                    all_nodes.add(caller_node)
                    all_nodes.add(callee_node)

    def _add_file_entity_edges(
        self,
        adjacency,
        all_nodes,
        entities,
    ):
        """Connect each entity to its containing file for traversal."""
        for entity in entities:
            file_node = _normalize_file_path(entity.filename)
            entity_node = entity.qualified_name

            self._add_edge(
                adjacency,
                file_node,
                entity_node,
                self.CONTAINS_RELATIONSHIP,
            )

            all_nodes.add(file_node)
            all_nodes.add(entity_node)

    def _add_import_edges(
        self,
        adjacency,
        all_nodes,
        dependencies,
        file_nodes,
    ):
        """Connect importing files to their internal dependency files."""
        known_modules = {}

        for path in file_nodes:
            if not path.endswith(".py"):
                continue

            module_name = self._module_name(path)
            known_modules.setdefault(module_name, path)

        for dependency in dependencies:
            if dependency.dependency_type != "internal":
                continue

            imported_module = dependency.imported_module
            if not imported_module:
                continue

            normalized_module = self._normalize_module(
                imported_module
            )
            target_file = known_modules.get(normalized_module)

            if target_file is None:
                continue

            source_file = _normalize_file_path(
                dependency.source_file
            )

            if source_file == target_file:
                continue

            self._add_edge(
                adjacency,
                source_file,
                target_file,
                self.IMPORT_RELATIONSHIP,
            )

            all_nodes.add(source_file)
            all_nodes.add(target_file)

    @staticmethod
    def _resolve_caller_node(source_file, caller, entity_map):
        candidates = entity_map.get(caller, ())

        for entity in candidates:
            if _normalize_file_path(entity.filename) == source_file:
                return entity.qualified_name

        return caller

    @staticmethod
    def _resolve_callee_nodes(callee, entity_map):
        if not isinstance(callee, str) or not callee:
            return ()

        exact = entity_map.get(callee)
        if exact:
            return (callee,)

        matches = []

        for qualified_name in entity_map:
            simple_name = qualified_name.rsplit(".", 1)[-1]

            if (
                callee == simple_name
                or callee.endswith("." + qualified_name)
            ):
                matches.append(qualified_name)

        return tuple(sorted(set(matches)))

    @staticmethod
    def _add_edge(adjacency, source, target, relationship):
        adjacency.setdefault(source, set()).add(
            (target, relationship)
        )

    @staticmethod
    def _reverse_edges(adjacency):
        reverse = {}

        for source, edges in adjacency.items():
            for target, relationship in edges:
                reverse.setdefault(target, set()).add(
                    (source, relationship)
                )

        return reverse

    def _trace_impacts(
        self,
        changed_nodes,
        reverse_adjacency,
        entity_map,
        max_depth,
    ):
        """Traverse reverse edges while hiding file-ownership transitions."""
        findings = {}
        queue = deque()

        for changed_node in sorted(changed_nodes):
            queue.append(
                (
                    changed_node,
                    changed_node,
                    (changed_node,),
                    (),
                    frozenset({changed_node}),
                )
            )

        visited_depth = {}

        while queue:
            (
                changed_target,
                current_node,
                path_nodes,
                relationships,
                path_visited,
            ) = queue.popleft()

            current_depth = len(relationships)

            neighbors = sorted(
                reverse_adjacency.get(current_node, ()),
                key=lambda item: (item[0], item[1]),
            )

            for dependent, relationship in neighbors:
                if dependent in path_visited:
                    continue

                is_ownership_transition = (
                    relationship == self.CONTAINS_RELATIONSHIP
                )

                if is_ownership_transition:
                    next_nodes = path_nodes
                    next_relationships = relationships
                    next_depth = current_depth
                else:
                    if current_depth >= max_depth:
                        continue

                    next_nodes = path_nodes + (dependent,)
                    next_relationships = relationships + (relationship,)
                    next_depth = current_depth + 1

                visit_key = (changed_target, dependent)
                previous_depth = visited_depth.get(visit_key)

                if (
                    previous_depth is not None
                    and previous_depth < next_depth
                ):
                    continue

                visited_depth[visit_key] = next_depth

                if not is_ownership_transition:
                    path = ImpactPath(
                        nodes=next_nodes,
                        relationship_types=next_relationships,
                    )

                    affected_file, affected_entity = (
                        self._describe_affected_node(
                            dependent,
                            entity_map,
                        )
                    )

                    if dependent not in changed_nodes:
                        finding = DirectIndirectImpactFinding(
                            changed_target=changed_target,
                            affected_file=affected_file,
                            affected_entity=affected_entity,
                            impact_type=(
                                "direct" if next_depth == 1 else "indirect"
                            ),
                            depth=next_depth,
                            relationship_types=next_relationships,
                            path=path,
                            reason=(
                                f"{affected_entity} is affected through "
                                f"{' -> '.join(next_nodes)}."
                            ),
                        )

                        key = (
                            changed_target,
                            dependent,
                            next_depth,
                            next_nodes,
                        )
                        findings[key] = finding

                queue.append(
                    (
                        changed_target,
                        dependent,
                        next_nodes,
                        next_relationships,
                        path_visited | {dependent},
                    )
                )

        return tuple(findings.values())

    @staticmethod
    def _describe_affected_node(node, entity_map):
        candidates = entity_map.get(node, ())

        if candidates:
            entity = candidates[0]
            return (
                _normalize_file_path(entity.filename),
                entity.qualified_name,
            )

        if node.endswith(".py") or "/" in node:
            return node, node

        return "<unknown>", node

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


def _normalize_file_path(value):
    if not isinstance(value, str) or not value.strip():
        raise DirectIndirectImpactDetectionError(
            "File paths must be non-empty strings."
        )

    normalized = value.strip().replace("\\", "/")

    if normalized.startswith("/") or (
        len(normalized) >= 2 and normalized[1] == ":"
    ):
        raise DirectIndirectImpactDetectionError(
            "File paths must be repository-relative."
        )

    parts = normalized.split("/")

    if any(part in {"", ".", ".."} for part in parts):
        raise DirectIndirectImpactDetectionError(
            "File path contains an invalid path segment."
        )

    return str(PurePosixPath(*parts))
