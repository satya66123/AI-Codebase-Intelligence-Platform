
from dataclasses import dataclass
from typing import Mapping

from app.application.call_graph_service import (
    CallGraphError,
    CallGraphService,
    CallRecord,
)
from app.application.code_entity_extractor import (
    CodeEntity,
    CodeEntityExtractionError,
    CodeEntityExtractor,
)
from app.application.language_parser import ParsedSource


class AdvancedCodeFlowTracingError(ValueError):
    """Raised when advanced code flow tracing fails."""


@dataclass(frozen=True)
class CodeFlowNode:
    """Represents a function, method, or module in the flow graph."""

    qualified_name: str
    entity_type: str
    filename: str
    line: int
    end_line: int | None = None


@dataclass(frozen=True)
class CodeFlowEdge:
    """Represents a resolved call relationship."""

    caller: str
    callee: str
    filename: str
    line: int
    call_type: str


@dataclass(frozen=True)
class CodeFlowTrace:
    """Represents one execution path through the call graph."""

    entry_point: str
    path: tuple[str, ...]
    edges: tuple[CodeFlowEdge, ...]
    depth: int
    is_recursive: bool
    terminated_by_depth_limit: bool


@dataclass(frozen=True)
class UnresolvedCall:
    """Represents a call that could not be mapped to a known entity."""

    caller: str
    callee: str
    filename: str
    line: int
    call_type: str


@dataclass(frozen=True)
class AdvancedCodeFlowTracingResult:
    """Contains repository-wide code flow tracing results."""

    total_files: int
    analyzed_files: int
    skipped_files: int
    total_entities: int
    total_calls: int
    resolved_calls: int
    unresolved_calls: int
    nodes: tuple[CodeFlowNode, ...]
    edges: tuple[CodeFlowEdge, ...]
    traces: tuple[CodeFlowTrace, ...]
    unresolved_call_records: tuple[UnresolvedCall, ...]
    entry_points: tuple[str, ...]

    @property
    def has_unresolved_calls(self) -> bool:
        return bool(self.unresolved_call_records)

    @property
    def has_traces(self) -> bool:
        return bool(self.traces)

    @property
    def recursive_traces(self) -> tuple[CodeFlowTrace, ...]:
        return tuple(
            trace for trace in self.traces if trace.is_recursive
        )

    @property
    def maximum_trace_depth(self) -> int:
        return max(
            (trace.depth for trace in self.traces),
            default=0,
        )


class AdvancedCodeFlowTracingService:
    """Build and trace a repository-wide function call graph."""

    SUPPORTED_LANGUAGE = "python"

    def __init__(
        self,
        call_graph_service: CallGraphService | None = None,
        code_entity_extractor: CodeEntityExtractor | None = None,
    ):
        self.call_graph_service = (
            call_graph_service or CallGraphService()
        )
        self.code_entity_extractor = (
            code_entity_extractor or CodeEntityExtractor()
        )

    def analyze(
        self,
        parsed_sources: Mapping[str, ParsedSource],
        entry_points: tuple[str, ...] | list[str] | None = None,
        max_depth: int = 10,
    ) -> AdvancedCodeFlowTracingResult:
        """Analyze source files and trace their function call flows."""

        self._validate_inputs(
            parsed_sources,
            entry_points,
            max_depth,
        )

        entities: list[CodeEntity] = []
        calls: list[CallRecord] = []
        analyzed_files = 0
        skipped_files = 0

        for filename, parsed_source in parsed_sources.items():
            if not isinstance(filename, str) or not filename.strip():
                raise AdvancedCodeFlowTracingError(
                    "Source file keys must be non-empty strings."
                )

            if not isinstance(parsed_source, ParsedSource):
                raise AdvancedCodeFlowTracingError(
                    f"Invalid ParsedSource for '{filename}'."
                )

            if parsed_source.filename != filename:
                raise AdvancedCodeFlowTracingError(
                    f"Source key '{filename}' does not match "
                    f"ParsedSource filename '{parsed_source.filename}'."
                )

            if parsed_source.language.lower() != self.SUPPORTED_LANGUAGE:
                skipped_files += 1
                continue

            try:
                file_entities = self.code_entity_extractor.extract(
                    parsed_source
                )
                call_result = self.call_graph_service.analyze(
                    parsed_source
                )
            except (
                CodeEntityExtractionError,
                CallGraphError,
            ) as exc:
                raise AdvancedCodeFlowTracingError(
                    f"Failed to analyze '{filename}': {exc}"
                ) from exc

            entities.extend(file_entities)
            calls.extend(call_result.calls)
            analyzed_files += 1

        nodes = self._build_nodes(entities)
        entity_lookup = self._build_entity_lookup(nodes)

        edges, unresolved = self._resolve_calls(
            calls,
            entity_lookup,
        )

        discovered_entry_points = self._discover_entry_points(
            nodes,
            edges,
        )

        selected_entry_points = (
            tuple(entry_points)
            if entry_points is not None
            else discovered_entry_points
        )

        self._validate_entry_points(
            selected_entry_points,
            entity_lookup,
        )

        traces = self._trace_flows(
            selected_entry_points,
            edges,
            max_depth,
        )

        return AdvancedCodeFlowTracingResult(
            total_files=len(parsed_sources),
            analyzed_files=analyzed_files,
            skipped_files=skipped_files,
            total_entities=len(entities),
            total_calls=len(calls),
            resolved_calls=len(edges),
            unresolved_calls=len(unresolved),
            nodes=nodes,
            edges=edges,
            traces=traces,
            unresolved_call_records=unresolved,
            entry_points=selected_entry_points,
        )

    def _validate_inputs(
        self,
        parsed_sources,
        entry_points,
        max_depth,
    ):
        if not isinstance(parsed_sources, Mapping):
            raise AdvancedCodeFlowTracingError(
                "parsed_sources must be a mapping."
            )

        if isinstance(max_depth, bool) or not isinstance(max_depth, int):
            raise AdvancedCodeFlowTracingError(
                "max_depth must be an integer."
            )

        if max_depth < 1:
            raise AdvancedCodeFlowTracingError(
                "max_depth must be greater than zero."
            )

        if entry_points is not None:
            if not isinstance(entry_points, (tuple, list)):
                raise AdvancedCodeFlowTracingError(
                    "entry_points must be a list or tuple."
                )

            if any(
                not isinstance(point, str) or not point.strip()
                for point in entry_points
            ):
                raise AdvancedCodeFlowTracingError(
                    "Entry points must contain non-empty strings."
                )

            if len(set(entry_points)) != len(entry_points):
                raise AdvancedCodeFlowTracingError(
                    "Entry points must not contain duplicates."
                )

    @staticmethod
    def _build_nodes(
        entities: list[CodeEntity],
    ) -> tuple[CodeFlowNode, ...]:
        nodes = []

        for entity in entities:
            nodes.append(
                CodeFlowNode(
                    qualified_name=entity.qualified_name,
                    entity_type=entity.entity_type,
                    filename=entity.filename,
                    line=entity.line,
                    end_line=entity.end_line,
                )
            )

        return tuple(
            sorted(
                nodes,
                key=lambda node: (
                    node.filename,
                    node.line,
                    node.qualified_name,
                ),
            )
        )

    @staticmethod
    def _build_entity_lookup(
        nodes: tuple[CodeFlowNode, ...],
    ) -> dict[str, CodeFlowNode]:
        lookup = {}

        for node in nodes:
            if node.entity_type not in ("function", "method"):
                continue

            lookup.setdefault(node.qualified_name, node)

        return lookup

    def _resolve_calls(
        self,
        calls: list[CallRecord],
        entity_lookup: dict[str, CodeFlowNode],
    ) -> tuple[
        tuple[CodeFlowEdge, ...],
        tuple[UnresolvedCall, ...],
    ]:
        edges = []
        unresolved = []

        for call in calls:
            resolved_caller = self._resolve_caller(
                call,
                entity_lookup,
            )

            resolved_callee = self._resolve_callee(
                call,
                entity_lookup,
            )

            if resolved_caller is None or resolved_callee is None:
                unresolved.append(
                    UnresolvedCall(
                        caller=call.caller,
                        callee=call.callee,
                        filename=call.filename,
                        line=call.line,
                        call_type=call.call_type,
                    )
                )
                continue

            edges.append(
                CodeFlowEdge(
                    caller=resolved_caller,
                    callee=resolved_callee,
                    filename=call.filename,
                    line=call.line,
                    call_type=call.call_type,
                )
            )

        return (
            tuple(
                sorted(
                    edges,
                    key=lambda edge: (
                        edge.filename,
                        edge.line,
                        edge.caller,
                        edge.callee,
                    ),
                )
            ),
            tuple(
                sorted(
                    unresolved,
                    key=lambda item: (
                        item.filename,
                        item.line,
                        item.caller,
                        item.callee,
                    ),
                )
            ),
        )

    @staticmethod
    def _resolve_caller(
        call: CallRecord,
        entity_lookup: dict[str, CodeFlowNode],
    ) -> str | None:
        candidates = [call.caller]

        if call.caller.startswith("<module>."):
            candidates.append(
                call.caller[len("<module>."):]
            )

        filename_stem = PathLike.stem(call.filename)

        candidates.extend(
            [
                f"{filename_stem}.{call.caller}",
                f"{filename_stem}."
                f"{call.caller.removeprefix(filename_stem + '.')}",
            ]
        )

        for candidate in candidates:
            if candidate in entity_lookup:
                return candidate

        return None

    @staticmethod
    def _resolve_callee(
        call: CallRecord,
        entity_lookup: dict[str, CodeFlowNode],
    ) -> str | None:
        callee = call.callee

        if callee == "<dynamic>":
            return None

        # Resolve instance and class method calls relative to
        # the class that owns the calling method.
        if callee.startswith(("self.", "cls.")):
            caller_parts = call.caller.split(".")

            if len(caller_parts) >= 3:
                class_qualified_name = ".".join(
                    caller_parts[:-1]
                )
                method_name = callee.split(".", 1)[1]
                candidate = (
                    f"{class_qualified_name}.{method_name}"
                )

                if candidate in entity_lookup:
                    return candidate

        # Resolve exact and uniquely matching qualified names.
        exact_matches = [
            name
            for name in entity_lookup
            if name == callee
            or name.endswith("." + callee)
        ]

        if len(exact_matches) == 1:
            return exact_matches[0]

        # Resolve calls to methods in the caller's enclosing scope.
        caller_parts = call.caller.split(".")

        caller_prefixes = [
            ".".join(caller_parts[:index])
            for index in range(len(caller_parts), 0, -1)
        ]

        for prefix in caller_prefixes:
            candidate = f"{prefix}.{callee}"

            if candidate in entity_lookup:
                return candidate

        return None

    @staticmethod
    def _discover_entry_points(
        nodes: tuple[CodeFlowNode, ...],
        edges: tuple[CodeFlowEdge, ...],
    ) -> tuple[str, ...]:
        called_functions = {
            edge.callee for edge in edges
        }

        candidates = {
            node.qualified_name
            for node in nodes
            if node.entity_type in ("function", "method")
            and node.qualified_name not in called_functions
        }

        return tuple(sorted(candidates))

    @staticmethod
    def _validate_entry_points(
        entry_points: tuple[str, ...],
        entity_lookup: dict[str, CodeFlowNode],
    ) -> None:
        for entry_point in entry_points:
            if entry_point not in entity_lookup:
                raise AdvancedCodeFlowTracingError(
                    f"Unknown entry point: '{entry_point}'."
                )

    def _trace_flows(
        self,
        entry_points: tuple[str, ...],
        edges: tuple[CodeFlowEdge, ...],
        max_depth: int,
    ) -> tuple[CodeFlowTrace, ...]:
        adjacency: dict[str, list[CodeFlowEdge]] = {}

        for edge in edges:
            adjacency.setdefault(edge.caller, []).append(edge)

        for outgoing in adjacency.values():
            outgoing.sort(
                key=lambda edge: (
                    edge.filename,
                    edge.line,
                    edge.callee,
                )
            )

        traces = []

        for entry_point in entry_points:
            self._walk(
                entry_point=entry_point,
                current=entry_point,
                path=(entry_point,),
                path_edges=(),
                adjacency=adjacency,
                max_depth=max_depth,
                traces=traces,
            )

        return tuple(
            sorted(
                traces,
                key=lambda trace: (
                    trace.entry_point,
                    trace.path,
                    trace.depth,
                ),
            )
        )

    def _walk(
        self,
        entry_point: str,
        current: str,
        path: tuple[str, ...],
        path_edges: tuple[CodeFlowEdge, ...],
        adjacency: dict[str, list[CodeFlowEdge]],
        max_depth: int,
        traces: list[CodeFlowTrace],
    ) -> None:
        outgoing = adjacency.get(current, [])

        if not outgoing:
            traces.append(
                CodeFlowTrace(
                    entry_point=entry_point,
                    path=path,
                    edges=path_edges,
                    depth=len(path_edges),
                    is_recursive=False,
                    terminated_by_depth_limit=False,
                )
            )
            return

        if len(path_edges) >= max_depth:
            traces.append(
                CodeFlowTrace(
                    entry_point=entry_point,
                    path=path,
                    edges=path_edges,
                    depth=len(path_edges),
                    is_recursive=False,
                    terminated_by_depth_limit=True,
                )
            )
            return

        for edge in outgoing:
            if edge.callee in path:
                traces.append(
                    CodeFlowTrace(
                        entry_point=entry_point,
                        path=path + (edge.callee,),
                        edges=path_edges + (edge,),
                        depth=len(path_edges) + 1,
                        is_recursive=True,
                        terminated_by_depth_limit=False,
                    )
                )
                continue

            self._walk(
                entry_point=entry_point,
                current=edge.callee,
                path=path + (edge.callee,),
                path_edges=path_edges + (edge,),
                adjacency=adjacency,
                max_depth=max_depth,
                traces=traces,
            )


class PathLike:
    """Small path helper that avoids changing the stored filename."""

    @staticmethod
    def stem(filename: str) -> str:
        normalized = filename.replace("\\", "/")
        return normalized.rsplit("/", 1)[-1].rsplit(".", 1)[0]
