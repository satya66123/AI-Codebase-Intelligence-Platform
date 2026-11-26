
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping, Iterable

from appy.application.call_graph_service import (
    CallGraphError,
    CallGraphService,
    CallRecord,
)
from appy.application.code_entity_extractor import (
    CodeEntity,
    CodeEntityExtractionError,
    CodeEntityExtractor,
)
from appy.application.language_parser import ParsedSource


class FunctionMethodExecutionPathError(ValueError):
    """Raised when function or method execution-path analysis fails."""


class ExecutionPathStatus:
    """Execution-path resolution statuses."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class FunctionExecutionStep:
    """A single function or method invocation in an execution path."""

    source_file: str
    caller: str
    callee: str
    target: str | None
    caller_type: str
    call_type: str
    line: int
    status: str


@dataclass(frozen=True)
class FunctionExecutionPath:
    """A traced execution path beginning at a function or method."""

    entry_point: str
    entry_file: str
    path: tuple[str, ...]
    steps: tuple[FunctionExecutionStep, ...]
    depth: int
    is_recursive: bool
    terminated_by_depth_limit: bool


@dataclass(frozen=True)
class UnresolvedExecutionCall:
    """A call that could not be resolved to a repository entity."""

    source_file: str
    caller: str
    callee: str
    line: int
    reason: str
    status: str


@dataclass(frozen=True)
class FunctionMethodExecutionPathResult:
    """Complete function and method execution-path analysis result."""

    total_files: int
    analyzed_files: int
    skipped_files: int
    total_entities: int
    total_functions: int
    total_methods: int
    total_calls: int
    resolved_calls: int
    unresolved_calls: int
    ambiguous_calls: int
    total_entry_points: int
    total_execution_paths: int
    maximum_execution_depth: int
    execution_paths: tuple[FunctionExecutionPath, ...]
    execution_steps: tuple[FunctionExecutionStep, ...]
    unresolved_references: tuple[UnresolvedExecutionCall, ...]

    @property
    def has_execution_paths(self) -> bool:
        return bool(self.execution_paths)

    @property
    def has_recursive_paths(self) -> bool:
        return any(path.is_recursive for path in self.execution_paths)

    @property
    def has_unresolved_calls(self) -> bool:
        return bool(self.unresolved_references)

    @property
    def healthy(self) -> bool:
        return self.unresolved_calls == 0 and self.ambiguous_calls == 0

    @property
    def recursive_paths(self) -> tuple[FunctionExecutionPath, ...]:
        return tuple(
            path for path in self.execution_paths if path.is_recursive
        )

    @property
    def depth_limited_paths(self) -> tuple[FunctionExecutionPath, ...]:
        return tuple(
            path
            for path in self.execution_paths
            if path.terminated_by_depth_limit
        )


class FunctionMethodExecutionPathService:
    """Trace function and method execution paths across Python modules."""

    BUILTIN_NAMES = {
        "abs", "all", "any", "ascii", "bin", "bool", "breakpoint",
        "bytearray", "bytes", "callable", "chr", "classmethod",
        "compile", "complex", "delattr", "dict", "dir", "divmod",
        "enumerate", "eval", "exec", "filter", "float", "format",
        "frozenset", "getattr", "globals", "hasattr", "hash", "help",
        "hex", "id", "input", "int", "isinstance", "issubclass",
        "iter", "len", "list", "locals", "map", "max", "memoryview",
        "min", "next", "object", "oct", "open", "ord", "pow",
        "print", "property", "range", "repr", "reversed", "round",
        "set", "setattr", "slice", "sorted", "staticmethod", "str",
        "sum", "super", "tuple", "type", "vars", "zip",
        "__import__",
    }

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
        entry_points: Iterable[str] | None = None,
        max_depth: int = 10,
    ) -> FunctionMethodExecutionPathResult:
        """Analyze function and method execution paths."""

        self._validate_inputs(
            parsed_sources,
            entry_points,
            max_depth,
        )

        calls: list[CallRecord] = []
        entities: list[CodeEntity] = []
        analyzed_files = 0
        skipped_files = 0
        module_stems: dict[str, str] = {}

        for source_key, parsed_source in parsed_sources.items():
            normalized_path = self._normalize_path(source_key)

            if parsed_source.filename != source_key:
                raise FunctionMethodExecutionPathError(
                    f"ParsedSource filename '{parsed_source.filename}' "
                    f"does not match mapping key '{source_key}'."
                )

            if parsed_source.language.lower() != "python":
                skipped_files += 1
                continue

            # Keep the semantic module name, but distinguish package
            # initializer files in the duplicate-check registry.
            module_name = self._get_module_name(normalized_path)
            path = PurePosixPath(normalized_path)

            duplicate_key = module_name

            if path.name == "__init__.py":
                duplicate_key = f"{module_name}.__init__"

            if duplicate_key in module_stems:
                raise FunctionMethodExecutionPathError(
                    f"Duplicate module name '{module_name}' was found "
                    f"in '{module_stems[duplicate_key]}' and "
                    f"'{normalized_path}'."
                )

            module_stems[duplicate_key] = normalized_path

            try:
                call_result = self.call_graph_service.analyze(
                    parsed_source
                )
                extracted_entities = self.code_entity_extractor.extract(
                    parsed_source
                )
            except (CallGraphError, CodeEntityExtractionError) as exc:
                raise FunctionMethodExecutionPathError(
                    f"Unable to analyze '{source_key}': {exc}"
                ) from exc

            analyzed_files += 1
            calls.extend(call_result.calls)
            entities.extend(extracted_entities)

        callable_entities = tuple(
            entity
            for entity in entities
            if entity.entity_type in ("function", "method")
        )

        entity_index = self._build_entity_index(callable_entities)

        resolved_steps: list[FunctionExecutionStep] = []
        unresolved_references: list[UnresolvedExecutionCall] = []

        for call in calls:
            if call.caller_type not in ("function", "method"):
                continue

            resolution_status, target = self._resolve_call(
                call,
                entity_index,
            )

            step = FunctionExecutionStep(
                source_file=self._normalize_path(call.filename),
                caller=call.caller,
                callee=call.callee,
                target=target,
                caller_type=call.caller_type,
                call_type=call.call_type,
                line=call.line,
                status=resolution_status,
            )

            resolved_steps.append(step)

            if resolution_status != ExecutionPathStatus.RESOLVED:
                unresolved_references.append(
                    UnresolvedExecutionCall(
                        source_file=step.source_file,
                        caller=step.caller,
                        callee=step.callee,
                        line=step.line,
                        reason=self._resolution_reason(
                            resolution_status
                        ),
                        status=resolution_status,
                    )
                )

        ordered_steps = tuple(
            sorted(
                resolved_steps,
                key=lambda step: (
                    step.source_file,
                    step.line,
                    step.caller,
                    step.callee,
                ),
            )
        )

        ordered_unresolved = tuple(
            sorted(
                unresolved_references,
                key=lambda item: (
                    item.source_file,
                    item.line,
                    item.caller,
                    item.callee,
                ),
            )
        )

        adjacency = self._build_adjacency(ordered_steps)

        selected_entry_points = self._select_entry_points(
            callable_entities,
            ordered_steps,
            entry_points,
        )

        paths: list[FunctionExecutionPath] = []

        for entity in selected_entry_points:
            self._trace_from_entry_point(
                entity=entity,
                adjacency=adjacency,
                max_depth=max_depth,
                paths=paths,
            )

        ordered_paths = tuple(
            sorted(
                paths,
                key=lambda path: (
                    path.entry_file,
                    path.entry_point,
                    path.path,
                ),
            )
        )

        resolved_count = sum(
            step.status == ExecutionPathStatus.RESOLVED
            for step in ordered_steps
        )
        ambiguous_count = sum(
            step.status == ExecutionPathStatus.AMBIGUOUS
            for step in ordered_steps
        )
        unresolved_count = sum(
            step.status == ExecutionPathStatus.UNRESOLVED
            for step in ordered_steps
        )

        functions_count = sum(
            entity.entity_type == "function"
            for entity in callable_entities
        )
        methods_count = sum(
            entity.entity_type == "method"
            for entity in callable_entities
        )

        return FunctionMethodExecutionPathResult(
            total_files=len(parsed_sources),
            analyzed_files=analyzed_files,
            skipped_files=skipped_files,
            total_entities=len(entities),
            total_functions=functions_count,
            total_methods=methods_count,
            total_calls=len(calls),
            resolved_calls=resolved_count,
            unresolved_calls=unresolved_count,
            ambiguous_calls=ambiguous_count,
            total_entry_points=len(selected_entry_points),
            total_execution_paths=len(ordered_paths),
            maximum_execution_depth=max(
                (path.depth for path in ordered_paths),
                default=0,
            ),
            execution_paths=ordered_paths,
            execution_steps=ordered_steps,
            unresolved_references=ordered_unresolved,
        )

    def _validate_inputs(
        self,
        parsed_sources: Mapping[str, ParsedSource],
        entry_points: Iterable[str] | None,
        max_depth: int,
    ) -> None:
        if not isinstance(parsed_sources, Mapping):
            raise FunctionMethodExecutionPathError(
                "parsed_sources must be a mapping."
            )

        if isinstance(max_depth, bool) or not isinstance(max_depth, int):
            raise FunctionMethodExecutionPathError(
                "max_depth must be an integer."
            )

        if max_depth < 1:
            raise FunctionMethodExecutionPathError(
                "max_depth must be greater than zero."
            )

        if entry_points is not None:
            if isinstance(entry_points, (str, bytes)):
                raise FunctionMethodExecutionPathError(
                    "entry_points must be an iterable of names, "
                    "not a single string."
                )

            if not isinstance(entry_points, (list, tuple)):
                raise FunctionMethodExecutionPathError(
                    "entry_points must be a list or tuple."
                )

            if any(
                not isinstance(name, str) or not name.strip()
                for name in entry_points
            ):
                raise FunctionMethodExecutionPathError(
                    "Entry-point names must be non-empty strings."
                )

            if len(set(entry_points)) != len(entry_points):
                raise FunctionMethodExecutionPathError(
                    "entry_points cannot contain duplicate names."
                )

        for source_key, parsed_source in parsed_sources.items():
            if not isinstance(source_key, str) or not source_key.strip():
                raise FunctionMethodExecutionPathError(
                    "Source file keys must be non-empty strings."
                )

            self._normalize_path(source_key)

            if not isinstance(parsed_source, ParsedSource):
                raise FunctionMethodExecutionPathError(
                    f"Invalid ParsedSource for '{source_key}'."
                )

    @staticmethod
    def _get_module_name(normalized_path: str) -> str:
        """Return the fully qualified module name for a Python source path.

        Package initializer files represent their containing package.
        For example:
            appy/__init__.py -> appy
            appy/application/__init__.py -> appy.application
            appy/application/service.py -> appy.application.service
        """
        path = PurePosixPath(normalized_path)

        if path.name == "__init__.py":
            module_parts = path.parent.parts

            # A root-level __init__.py has no containing package path.
            if not module_parts:
                return path.stem
        else:
            module_parts = path.with_suffix("").parts

        return ".".join(module_parts)

    @staticmethod
    def _normalize_path(source_path: str) -> str:
        normalized = source_path.replace("\\", "/").strip()

        if (
            not normalized
            or normalized.startswith("/")
            or any(
                part in ("", ".", "..")
                for part in normalized.split("/")
            )
        ):
            raise FunctionMethodExecutionPathError(
                f"Invalid relative source path '{source_path}'."
            )

        return normalized

    @staticmethod
    def _build_entity_index(
        entities: tuple[CodeEntity, ...],
    ) -> dict[str, list[CodeEntity]]:
        index: dict[str, list[CodeEntity]] = {}

        for entity in entities:
            index.setdefault(entity.name, []).append(entity)
            index.setdefault(entity.qualified_name, []).append(entity)

        for candidates in index.values():
            candidates.sort(
                key=lambda entity: (
                    entity.filename,
                    entity.qualified_name,
                )
            )

        return index

    def _resolve_call(
        self,
        call: CallRecord,
        entity_index: dict[str, list[CodeEntity]],
    ) -> tuple[str, str | None]:
        """Resolve a call to a repository function or method."""

        if call.callee == "<dynamic>":
            return ExecutionPathStatus.UNRESOLVED, None

        candidates: list[CodeEntity] = []
        caller_entity = self._find_caller_entity(
            call.caller,
            entity_index,
        )

        if call.call_type == "function":
            candidates.extend(entity_index.get(call.callee, []))

        elif call.call_type == "attribute":
            parts = call.callee.split(".")

            if len(parts) >= 2:
                prefix = parts[0]
                symbol = parts[-1]

                if prefix in ("self", "cls") and caller_entity:
                    parent = caller_entity.parent
                    if parent:
                        qualified = f"{parent}.{symbol}"
                        candidates.extend(
                            entity_index.get(qualified, [])
                        )

                else:
                    candidates.extend(
                        self._qualified_attribute_candidates(
                            call.callee,
                            entity_index,
                        )
                    )

            else:
                candidates.extend(entity_index.get(call.callee, []))

        candidates = self._unique_entities(candidates)

        if caller_entity:
            same_file = [
                candidate
                for candidate in candidates
                if candidate.filename == caller_entity.filename
            ]

            if same_file:
                candidates = same_file

        if not candidates:
            if self._is_known_external_call(call.callee):
                return ExecutionPathStatus.UNRESOLVED, None

            return ExecutionPathStatus.UNRESOLVED, None

        if len(candidates) > 1:
            return ExecutionPathStatus.AMBIGUOUS, None

        return (
            ExecutionPathStatus.RESOLVED,
            candidates[0].qualified_name,
        )

    @staticmethod
    def _find_caller_entity(
        caller: str,
        entity_index: dict[str, list[CodeEntity]],
    ) -> CodeEntity | None:
        candidates = entity_index.get(caller, [])

        if not candidates:
            return None

        return candidates[0]

    @staticmethod
    def _qualified_attribute_candidates(
        callee: str,
        entity_index: dict[str, list[CodeEntity]],
    ) -> list[CodeEntity]:
        parts = callee.split(".")
        symbol = parts[-1]
        prefix = ".".join(parts[:-1])

        candidates = list(
            entity_index.get(f"{prefix}.{symbol}", [])
        )

        if not candidates:
            candidates.extend(entity_index.get(symbol, []))

        return candidates

    @staticmethod
    def _unique_entities(
        entities: list[CodeEntity],
    ) -> list[CodeEntity]:
        unique = {
            (entity.filename, entity.qualified_name): entity
            for entity in entities
        }

        return sorted(
            unique.values(),
            key=lambda entity: (
                entity.filename,
                entity.qualified_name,
            ),
        )

    def _is_known_external_call(self, callee: str) -> bool:
        return (
            callee in self.BUILTIN_NAMES
            or callee.split(".")[-1] in self.BUILTIN_NAMES
        )

    @staticmethod
    def _resolution_reason(status: str) -> str:
        if status == ExecutionPathStatus.AMBIGUOUS:
            return (
                "Multiple repository entities match this call; "
                "the target cannot be selected uniquely."
            )

        return (
            "The call could not be resolved to a repository "
            "function or method."
        )

    @staticmethod
    def _build_adjacency(
        steps: tuple[FunctionExecutionStep, ...],
    ) -> dict[str, list[FunctionExecutionStep]]:
        adjacency: dict[str, list[FunctionExecutionStep]] = {}

        for step in steps:
            if (
                step.status != ExecutionPathStatus.RESOLVED
                or step.target is None
            ):
                continue

            adjacency.setdefault(step.caller, []).append(step)

        for outgoing in adjacency.values():
            outgoing.sort(
                key=lambda step: (
                    step.line,
                    step.target or "",
                )
            )

        return adjacency

    def _select_entry_points(
        self,
        entities: tuple[CodeEntity, ...],
        steps: tuple[FunctionExecutionStep, ...],
        requested_entry_points: Iterable[str] | None,
    ) -> tuple[CodeEntity, ...]:
        if requested_entry_points is not None:
            selected = []

            for name in requested_entry_points:
                matches = [
                    entity
                    for entity in entities
                    if entity.qualified_name == name
                    or entity.name == name
                ]

                if not matches:
                    raise FunctionMethodExecutionPathError(
                        f"Entry point '{name}' was not found."
                    )

                if len(matches) > 1:
                    raise FunctionMethodExecutionPathError(
                        f"Entry point '{name}' is ambiguous. "
                        "Use its qualified name."
                    )

                selected.append(matches[0])

            return tuple(
                sorted(
                    selected,
                    key=lambda entity: entity.qualified_name,
                )
            )

        called_targets = {
            step.target
            for step in steps
            if step.status == ExecutionPathStatus.RESOLVED
        }

        roots = [
            entity
            for entity in entities
            if entity.qualified_name not in called_targets
        ]

        # If every callable participates in a cycle, retain all entities
        # as possible roots so recursive paths are still observable.
        if not roots:
            roots = list(entities)

        return tuple(
            sorted(
                roots,
                key=lambda entity: (
                    entity.filename,
                    entity.qualified_name,
                ),
            )
        )

    def _trace_from_entry_point(
        self,
        entity: CodeEntity,
        adjacency: dict[str, list[FunctionExecutionStep]],
        max_depth: int,
        paths: list[FunctionExecutionPath],
    ) -> None:
        root = entity.qualified_name

        self._walk(
            entry_point=root,
            entry_file=entity.filename,
            current=root,
            path=(root,),
            steps=(),
            adjacency=adjacency,
            max_depth=max_depth,
            paths=paths,
        )

    def _walk(
        self,
        entry_point: str,
        entry_file: str,
        current: str,
        path: tuple[str, ...],
        steps: tuple[FunctionExecutionStep, ...],
        adjacency: dict[str, list[FunctionExecutionStep]],
        max_depth: int,
        paths: list[FunctionExecutionPath],
    ) -> None:
        outgoing = adjacency.get(current, [])

        if not outgoing:
            paths.append(
                FunctionExecutionPath(
                    entry_point=entry_point,
                    entry_file=entry_file,
                    path=path,
                    steps=steps,
                    depth=len(steps),
                    is_recursive=False,
                    terminated_by_depth_limit=False,
                )
            )
            return

        if len(steps) >= max_depth:
            paths.append(
                FunctionExecutionPath(
                    entry_point=entry_point,
                    entry_file=entry_file,
                    path=path,
                    steps=steps,
                    depth=len(steps),
                    is_recursive=False,
                    terminated_by_depth_limit=True,
                )
            )
            return

        for step in outgoing:
            target = step.target

            if target is None:
                continue

            next_path = path + (target,)
            next_steps = steps + (step,)

            if target in path:
                paths.append(
                    FunctionExecutionPath(
                        entry_point=entry_point,
                        entry_file=entry_file,
                        path=next_path,
                        steps=next_steps,
                        depth=len(next_steps),
                        is_recursive=True,
                        terminated_by_depth_limit=False,
                    )
                )
                continue

            self._walk(
                entry_point=entry_point,
                entry_file=entry_file,
                current=target,
                path=next_path,
                steps=next_steps,
                adjacency=adjacency,
                max_depth=max_depth,
                paths=paths,
            )
