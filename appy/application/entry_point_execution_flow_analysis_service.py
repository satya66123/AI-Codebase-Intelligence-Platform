
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from appy.application.call_graph_service import (
    CallGraphError,
    CallGraphService,
    CallRecord,
)
from appy.application.language_parser import ParsedSource
from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import RepositoryScanResult


class EntryPointExecutionFlowError(ValueError):
    """Raised when entry-point or execution-flow analysis fails."""


class EntryPointType:
    """Supported entry-point classification values."""

    MAIN_GUARD = "main_guard"
    CONVENTIONAL = "conventional_candidate"


@dataclass(frozen=True)
class EntryPointFinding:
    """Represents a discovered or potential application entry point."""

    file_path: str
    entry_point_type: str
    confirmed: bool
    line: int | None
    function_names: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class ExecutionFlowStep:
    """Represents a call made during entry-point execution."""

    file_path: str
    caller: str
    callee: str
    caller_type: str
    call_type: str
    line: int


@dataclass(frozen=True)
class EntryPointExecutionTrace:
    """Represents a sequence of calls originating from an entry point."""

    entry_point: str
    file_path: str
    path: tuple[str, ...]
    steps: tuple[ExecutionFlowStep, ...]
    depth: int
    is_recursive: bool
    terminated_by_depth_limit: bool


@dataclass(frozen=True)
class EntryPointExecutionFlowResult:
    """Contains entry-point findings and execution-flow analysis."""

    repository_name: str
    total_repository_files: int
    analyzed_python_files: int
    skipped_files: int
    confirmed_entry_points: int
    conventional_candidates: int
    total_entry_points: int
    total_calls: int
    execution_steps: int
    unresolved_calls: int
    entry_points: tuple[EntryPointFinding, ...]
    execution_steps_records: tuple[ExecutionFlowStep, ...]
    traces: tuple[EntryPointExecutionTrace, ...]

    @property
    def has_entry_points(self) -> bool:
        return bool(self.entry_points)

    @property
    def has_confirmed_entry_points(self) -> bool:
        return any(item.confirmed for item in self.entry_points)

    @property
    def has_execution_flows(self) -> bool:
        return bool(self.traces)

    @property
    def confirmed_findings(self) -> tuple[EntryPointFinding, ...]:
        return tuple(
            item for item in self.entry_points if item.confirmed
        )

    @property
    def candidate_findings(self) -> tuple[EntryPointFinding, ...]:
        return tuple(
            item for item in self.entry_points if not item.confirmed
        )

    @property
    def maximum_trace_depth(self) -> int:
        return max(
            (trace.depth for trace in self.traces),
            default=0,
        )


class _MainGuardVisitor(ast.NodeVisitor):
    """Find module-level Python main execution guards."""

    def __init__(self):
        self.lines: list[int] = []

    def visit_If(self, node: ast.If):
        if self._is_main_guard(node.test):
            self.lines.append(node.lineno)

        self.generic_visit(node)

    @staticmethod
    def _is_main_guard(test: ast.AST) -> bool:
        if not isinstance(test, ast.Compare):
            return False

        if len(test.ops) != 1 or len(test.comparators) != 1:
            return False

        left = test.left
        right = test.comparators[0]

        return (
            isinstance(test.ops[0], ast.Eq)
            and isinstance(left, ast.Name)
            and left.id == "__name__"
            and isinstance(right, ast.Constant)
            and right.value == "__main__"
        ) or (
            isinstance(test.ops[0], ast.Eq)
            and isinstance(right, ast.Name)
            and right.id == "__name__"
            and isinstance(left, ast.Constant)
            and left.value == "__main__"
        )


class EntryPointExecutionFlowAnalysisService:
    """Discover Python entry points and analyze their execution calls."""

    CONVENTIONAL_FILENAMES = {
        "main.py",
        "appy.py",
        "run.py",
        "manage.py",
        "wsgi.py",
        "asgi.py",
        "__main__.py",
    }

    SUPPORTED_LANGUAGE = "python"

    def __init__(
        self,
        call_graph_service: CallGraphService | None = None,
    ):
        self.call_graph_service = (
            call_graph_service or CallGraphService()
        )

    def analyze(
        self,
        repository: RepositoryInfo,
        scan_result: RepositoryScanResult,
        parsed_sources: Mapping[str, ParsedSource],
        max_depth: int = 10,
    ) -> EntryPointExecutionFlowResult:
        """Analyze entry points and execution flows in a repository."""

        self._validate_inputs(
            repository,
            scan_result,
            parsed_sources,
            max_depth,
        )

        # Keep every scanned file here. Language filtering happens
        # only after confirming that the supplied file belongs to
        # the repository scan.
        scanned_files = {
            self._relative_path(repository.root, path)
            for path in scan_result.files
        }

        findings: dict[str, EntryPointFinding] = {}
        all_calls: list[CallRecord] = []
        analyzed_files = 0
        skipped_files = 0

        for source_key, parsed_source in parsed_sources.items():
            relative_path = self._normalize_source_key(source_key)

            if relative_path not in scanned_files:
                raise EntryPointExecutionFlowError(
                    f"Source file '{source_key}' was not found "
                    "in the repository scan."
                )

            if not isinstance(parsed_source, ParsedSource):
                raise EntryPointExecutionFlowError(
                    f"Invalid ParsedSource for '{source_key}'."
                )

            if parsed_source.filename != source_key:
                raise EntryPointExecutionFlowError(
                    f"ParsedSource filename '{parsed_source.filename}' "
                    f"does not match source key '{source_key}'."
                )

            # Unsupported languages are valid scanned inputs,
            # but are not analyzed by this Python-specific service.
            if parsed_source.language.lower() != self.SUPPORTED_LANGUAGE:
                skipped_files += 1
                continue

            if not isinstance(parsed_source.tree, ast.Module):
                raise EntryPointExecutionFlowError(
                    f"'{source_key}' does not contain a Python AST module."
                )

            try:
                call_result = self.call_graph_service.analyze(
                    parsed_source
                )
            except CallGraphError as exc:
                raise EntryPointExecutionFlowError(
                    f"Unable to analyze '{source_key}': {exc}"
                ) from exc

            analyzed_files += 1
            all_calls.extend(call_result.calls)

            main_guard_lines = self._find_main_guards(
                parsed_source.tree
            )

            if main_guard_lines:
                function_names = self._get_guard_function_calls(
                    call_result.calls,
                    parsed_source.filename,
                )

                findings[relative_path] = EntryPointFinding(
                    file_path=relative_path,
                    entry_point_type=EntryPointType.MAIN_GUARD,
                    confirmed=True,
                    line=main_guard_lines[0],
                    function_names=function_names,
                    description=(
                        "Python module contains an "
                        "if __name__ == '__main__' execution guard."
                    ),
                )

            elif Path(relative_path).name.lower() in (
                self.CONVENTIONAL_FILENAMES
            ):
                findings[relative_path] = EntryPointFinding(
                    file_path=relative_path,
                    entry_point_type=EntryPointType.CONVENTIONAL,
                    confirmed=False,
                    line=None,
                    function_names=(),
                    description=(
                        "Filename follows a conventional Python "
                        "application entry-point naming pattern. "
                        "Execution is not confirmed."
                    ),
                )

        ordered_findings = tuple(
            sorted(
                findings.values(),
                key=lambda item: (
                    not item.confirmed,
                    item.file_path.lower(),
                ),
            )
        )

        steps = self._build_execution_steps(
            all_calls,
            findings,
        )

        traces = self._build_traces(
            findings,
            steps,
            max_depth,
        )

        unresolved_count = sum(
            1
            for call in all_calls
            if not self._is_resolved_call(call, all_calls)
        )

        confirmed_count = sum(
            1 for item in ordered_findings if item.confirmed
        )

        candidate_count = sum(
            1 for item in ordered_findings if not item.confirmed
        )

        return EntryPointExecutionFlowResult(
            repository_name=repository.name,
            total_repository_files=scan_result.total_files,
            analyzed_python_files=analyzed_files,
            skipped_files=skipped_files,
            confirmed_entry_points=confirmed_count,
            conventional_candidates=candidate_count,
            total_entry_points=len(ordered_findings),
            total_calls=len(all_calls),
            execution_steps=len(steps),
            unresolved_calls=unresolved_count,
            entry_points=ordered_findings,
            execution_steps_records=steps,
            traces=traces,
        )

    def _validate_inputs(
        self,
        repository,
        scan_result,
        parsed_sources,
        max_depth,
    ) -> None:
        if not isinstance(repository, RepositoryInfo):
            raise EntryPointExecutionFlowError(
                "A valid RepositoryInfo object is required."
            )

        if not isinstance(scan_result, RepositoryScanResult):
            raise EntryPointExecutionFlowError(
                "A valid RepositoryScanResult object is required."
            )

        if not isinstance(parsed_sources, Mapping):
            raise EntryPointExecutionFlowError(
                "parsed_sources must be a mapping."
            )

        if isinstance(max_depth, bool) or not isinstance(max_depth, int):
            raise EntryPointExecutionFlowError(
                "max_depth must be an integer."
            )

        if max_depth < 1:
            raise EntryPointExecutionFlowError(
                "max_depth must be greater than zero."
            )

        try:
            repository_root = repository.root.resolve()
            scan_root = scan_result.root.resolve()
        except (OSError, RuntimeError, AttributeError) as exc:
            raise EntryPointExecutionFlowError(
                "Unable to resolve repository scan paths."
            ) from exc

        if repository_root != scan_root:
            raise EntryPointExecutionFlowError(
                "Repository information and scan result roots do not match."
            )

        for source_key, parsed_source in parsed_sources.items():
            if not isinstance(source_key, str) or not source_key.strip():
                raise EntryPointExecutionFlowError(
                    "Source mapping keys must be non-empty strings."
                )

            if not isinstance(parsed_source, ParsedSource):
                raise EntryPointExecutionFlowError(
                    f"Invalid ParsedSource for '{source_key}'."
                )

    @staticmethod
    def _relative_path(root: Path, path: Path) -> str:
        try:
            return path.resolve().relative_to(
                root.resolve()
            ).as_posix()
        except (ValueError, OSError, RuntimeError) as exc:
            raise EntryPointExecutionFlowError(
                f"File '{path}' is outside the repository root."
            ) from exc

    @staticmethod
    def _normalize_source_key(source_key: str) -> str:
        normalized = source_key.replace("\\", "/").strip()

        if (
            not normalized
            or normalized.startswith("/")
            or any(
                part in ("", ".", "..")
                for part in normalized.split("/")
            )
        ):
            raise EntryPointExecutionFlowError(
                f"Invalid relative source path: '{source_key}'."
            )

        return normalized

    @staticmethod
    def _find_main_guards(tree: ast.Module) -> tuple[int, ...]:
        visitor = _MainGuardVisitor()

        for node in tree.body:
            if isinstance(node, ast.If):
                visitor.visit(node)

        return tuple(sorted(set(visitor.lines)))

    @staticmethod
    def _get_guard_function_calls(
        calls: tuple[CallRecord, ...],
        filename: str,
    ) -> tuple[str, ...]:
        module_name = Path(filename).stem

        names = {
            f"{module_name}.{call.callee}"
            for call in calls
            if call.filename == filename
            and call.caller == module_name
            and call.call_type == "function"
            and call.callee != "<dynamic>"
        }

        return tuple(sorted(names))

    @staticmethod
    def _build_execution_steps(
        calls: list[CallRecord],
        findings: dict[str, EntryPointFinding],
    ) -> tuple[ExecutionFlowStep, ...]:
        confirmed_files = {
            path
            for path, finding in findings.items()
            if finding.confirmed
        }

        steps = []

        for call in calls:
            relative_filename = call.filename.replace("\\", "/")

            if relative_filename not in confirmed_files:
                continue

            steps.append(
                ExecutionFlowStep(
                    file_path=relative_filename,
                    caller=call.caller,
                    callee=call.callee,
                    caller_type=call.caller_type,
                    call_type=call.call_type,
                    line=call.line,
                )
            )

        return tuple(
            sorted(
                steps,
                key=lambda step: (
                    step.file_path,
                    step.line,
                    step.caller,
                    step.callee,
                ),
            )
        )

    def _build_traces(
        self,
        findings: dict[str, EntryPointFinding],
        steps: tuple[ExecutionFlowStep, ...],
        max_depth: int,
    ) -> tuple[EntryPointExecutionTrace, ...]:
        traces = []

        for file_path, finding in findings.items():
            if not finding.confirmed:
                continue

            module_name = Path(file_path).stem
            file_steps = tuple(
                step for step in steps if step.file_path == file_path
            )

            adjacency: dict[str, list[ExecutionFlowStep]] = {}

            for step in file_steps:
                adjacency.setdefault(step.caller, []).append(step)

            for outgoing in adjacency.values():
                outgoing.sort(
                    key=lambda step: (
                        step.line,
                        step.callee,
                    )
                )

            for root in finding.function_names:
                display_root = root.rsplit(".", 1)[-1]

                if root not in adjacency:
                    traces.append(
                        EntryPointExecutionTrace(
                            entry_point=root,
                            file_path=file_path,
                            path=(display_root,),
                            steps=(),
                            depth=0,
                            is_recursive=False,
                            terminated_by_depth_limit=False,
                        )
                    )
                    continue

                self._walk_execution_flow(
                    entry_point=root,
                    current=root,
                    module_name=module_name,
                    file_path=file_path,
                    path=(display_root,),
                    path_steps=(),
                    adjacency=adjacency,
                    max_depth=max_depth,
                    traces=traces,
                )

        return tuple(
            sorted(
                traces,
                key=lambda trace: (
                    trace.file_path,
                    trace.entry_point,
                    trace.path,
                ),
            )
        )

    def _walk_execution_flow(
        self,
        entry_point: str,
        current: str,
        module_name: str,
        file_path: str,
        path: tuple[str, ...],
        path_steps: tuple[ExecutionFlowStep, ...],
        adjacency: dict[str, list[ExecutionFlowStep]],
        max_depth: int,
        traces: list[EntryPointExecutionTrace],
    ) -> None:
        outgoing = adjacency.get(current, [])

        if not outgoing:
            traces.append(
                EntryPointExecutionTrace(
                    entry_point=entry_point,
                    file_path=file_path,
                    path=path,
                    steps=path_steps,
                    depth=len(path_steps),
                    is_recursive=False,
                    terminated_by_depth_limit=False,
                )
            )
            return

        if len(path_steps) >= max_depth:
            traces.append(
                EntryPointExecutionTrace(
                    entry_point=entry_point,
                    file_path=file_path,
                    path=path,
                    steps=path_steps,
                    depth=len(path_steps),
                    is_recursive=False,
                    terminated_by_depth_limit=True,
                )
            )
            return

        for step in outgoing:
            next_node = self._qualify_local_callee(
                step.callee,
                module_name,
            )

            next_path = path + (next_node,)
            next_steps = path_steps + (step,)

            if next_node in path:
                traces.append(
                    EntryPointExecutionTrace(
                        entry_point=entry_point,
                        file_path=file_path,
                        path=next_path,
                        steps=next_steps,
                        depth=len(next_steps),
                        is_recursive=True,
                        terminated_by_depth_limit=False,
                    )
                )
                continue

            self._walk_execution_flow(
                entry_point=entry_point,
                current=next_node,
                module_name=module_name,
                file_path=file_path,
                path=next_path,
                path_steps=next_steps,
                adjacency=adjacency,
                max_depth=max_depth,
                traces=traces,
            )

    @staticmethod
    def _qualify_local_callee(
        callee: str,
        module_name: str,
    ) -> str:
        if callee and callee != "<dynamic>" and "." not in callee:
            return f"{module_name}.{callee}"

        return callee

    @staticmethod
    def _is_resolved_call(
        call: CallRecord,
        all_calls: list[CallRecord],
    ) -> bool:
        if call.callee == "<dynamic>":
            return False

        if call.call_type == "function":
            return any(
                candidate.caller == call.callee
                or candidate.caller.endswith("." + call.callee)
                for candidate in all_calls
            )

        if call.call_type == "attribute":
            return any(
                candidate.caller.endswith(
                    "." + call.callee.split(".")[-1]
                )
                for candidate in all_calls
            )

        return False
