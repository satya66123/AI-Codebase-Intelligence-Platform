
"""Analyze structural and cognitive complexity of Python source files."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Mapping


class CodeComplexityAnalysisError(ValueError):
    """Raised when complexity analysis receives invalid input."""


class ComplexitySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class FunctionComplexity:
    file_path: str
    name: str
    qualified_name: str
    line: int
    end_line: int
    lines: int
    parameter_count: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    max_nesting_depth: int
    severity: ComplexitySeverity

    def __post_init__(self) -> None:
        if not self.file_path or not isinstance(self.file_path, str):
            raise ValueError("file_path must be a non-empty string.")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string.")
        if not isinstance(self.qualified_name, str) or not self.qualified_name:
            raise ValueError("qualified_name must be a non-empty string.")
        for field_name in (
            "line", "end_line", "lines", "parameter_count",
            "cyclomatic_complexity", "cognitive_complexity",
            "max_nesting_depth",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.line < 1 or self.end_line < self.line:
            raise ValueError("Function line range is invalid.")
        if not isinstance(self.severity, ComplexitySeverity):
            raise TypeError("severity must be a ComplexitySeverity.")


@dataclass(frozen=True)
class FileComplexityResult:
    file_path: str
    lines_of_code: int
    function_count: int
    average_cyclomatic_complexity: float
    maximum_cyclomatic_complexity: int
    average_cognitive_complexity: float
    maximum_cognitive_complexity: int
    maximum_nesting_depth: int
    functions: tuple[FunctionComplexity, ...]
    syntax_valid: bool = True
    syntax_error: str = ""

    def __post_init__(self) -> None:
        if not self.file_path:
            raise ValueError("file_path must not be empty.")
        for field_name in (
            "lines_of_code", "function_count",
            "maximum_cyclomatic_complexity",
            "maximum_cognitive_complexity", "maximum_nesting_depth",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if not isinstance(self.functions, tuple):
            raise TypeError("functions must be a tuple.")
        if not isinstance(self.syntax_valid, bool):
            raise TypeError("syntax_valid must be a boolean.")
        if not isinstance(self.syntax_error, str):
            raise TypeError("syntax_error must be a string.")


@dataclass(frozen=True)
class CodeComplexityAnalysisResult:
    total_files: int
    analyzed_files: int
    skipped_files: int
    total_functions: int
    total_lines_of_code: int
    average_cyclomatic_complexity: float
    maximum_cyclomatic_complexity: int
    average_cognitive_complexity: float
    maximum_cognitive_complexity: int
    maximum_nesting_depth: int
    file_results: tuple[FileComplexityResult, ...]
    functions: tuple[FunctionComplexity, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "total_files", "analyzed_files", "skipped_files",
            "total_functions", "total_lines_of_code",
            "maximum_cyclomatic_complexity",
            "maximum_cognitive_complexity", "maximum_nesting_depth",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.analyzed_files + self.skipped_files != self.total_files:
            raise ValueError("Analyzed and skipped files must equal total files.")
        if self.total_functions != len(self.functions):
            raise ValueError("total_functions must match functions.")
        if not isinstance(self.file_results, tuple):
            raise TypeError("file_results must be a tuple.")
        if not isinstance(self.functions, tuple):
            raise TypeError("functions must be a tuple.")

    @property
    def high_complexity_functions(self) -> tuple[FunctionComplexity, ...]:
        return tuple(
            function for function in self.functions
            if function.severity in (
                ComplexitySeverity.HIGH,
                ComplexitySeverity.CRITICAL,
            )
        )

    @property
    def critical_complexity_functions(self) -> tuple[FunctionComplexity, ...]:
        return tuple(
            function for function in self.functions
            if function.severity == ComplexitySeverity.CRITICAL
        )

    @property
    def syntax_error_count(self) -> int:
        return sum(not result.syntax_valid for result in self.file_results)


class CodeComplexityAnalysisService:
    """Calculate complexity metrics from Python source code.

    Cyclomatic complexity starts at 1 and increases for decisions:
    if/elif, loops, except handlers, conditional expressions, boolean
    operators, and comprehension filters.

    Cognitive complexity is a lightweight, documented heuristic:
    control-flow structures add one plus their nesting level; boolean
    operator changes add one; recursion is not assessed.
    """

    DEFAULT_HIGH_CYCLOMATIC = 10
    DEFAULT_CRITICAL_CYCLOMATIC = 20
    DEFAULT_HIGH_COGNITIVE = 15
    DEFAULT_CRITICAL_COGNITIVE = 30
    DEFAULT_HIGH_NESTING = 4
    DEFAULT_CRITICAL_NESTING = 6

    def __init__(
        self,
        high_cyclomatic_threshold: int = DEFAULT_HIGH_CYCLOMATIC,
        critical_cyclomatic_threshold: int = DEFAULT_CRITICAL_CYCLOMATIC,
        high_cognitive_threshold: int = DEFAULT_HIGH_COGNITIVE,
        critical_cognitive_threshold: int = DEFAULT_CRITICAL_COGNITIVE,
        high_nesting_threshold: int = DEFAULT_HIGH_NESTING,
        critical_nesting_threshold: int = DEFAULT_CRITICAL_NESTING,
    ) -> None:
        thresholds = {
            "high_cyclomatic_threshold": high_cyclomatic_threshold,
            "critical_cyclomatic_threshold": critical_cyclomatic_threshold,
            "high_cognitive_threshold": high_cognitive_threshold,
            "critical_cognitive_threshold": critical_cognitive_threshold,
            "high_nesting_threshold": high_nesting_threshold,
            "critical_nesting_threshold": critical_nesting_threshold,
        }
        for name, value in thresholds.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise CodeComplexityAnalysisError(
                    f"{name} must be a positive integer."
                )

        if critical_cyclomatic_threshold < high_cyclomatic_threshold:
            raise CodeComplexityAnalysisError(
                "Critical cyclomatic threshold must be >= high threshold."
            )
        if critical_cognitive_threshold < high_cognitive_threshold:
            raise CodeComplexityAnalysisError(
                "Critical cognitive threshold must be >= high threshold."
            )
        if critical_nesting_threshold < high_nesting_threshold:
            raise CodeComplexityAnalysisError(
                "Critical nesting threshold must be >= high threshold."
            )

        self.high_cyclomatic_threshold = high_cyclomatic_threshold
        self.critical_cyclomatic_threshold = critical_cyclomatic_threshold
        self.high_cognitive_threshold = high_cognitive_threshold
        self.critical_cognitive_threshold = critical_cognitive_threshold
        self.high_nesting_threshold = high_nesting_threshold
        self.critical_nesting_threshold = critical_nesting_threshold

    def analyze(
        self, source_files: Mapping[str, str]
    ) -> CodeComplexityAnalysisResult:
        if not isinstance(source_files, Mapping):
            raise CodeComplexityAnalysisError(
                "source_files must be a mapping of relative paths to source text."
            )

        normalized: dict[str, str] = {}
        for raw_path, content in source_files.items():
            path = self._validate_path(raw_path)
            if path in normalized:
                raise CodeComplexityAnalysisError(
                    f"Duplicate normalized source path: {path}"
                )
            if not isinstance(content, str):
                raise CodeComplexityAnalysisError(
                    f"Source content for '{path}' must be a string."
                )
            normalized[path] = content

        file_results: list[FileComplexityResult] = []
        all_functions: list[FunctionComplexity] = []
        total_lines = 0
        analyzed = 0
        skipped = 0

        for path, content in sorted(normalized.items()):
            if PurePosixPath(path).suffix.lower() not in {".py", ".pyw"}:
                skipped += 1
                continue

            analyzed += 1
            result = self._analyze_file(path, content)
            file_results.append(result)
            all_functions.extend(result.functions)
            total_lines += result.lines_of_code

        cyclomatic = [f.cyclomatic_complexity for f in all_functions]
        cognitive = [f.cognitive_complexity for f in all_functions]

        return CodeComplexityAnalysisResult(
            total_files=len(normalized),
            analyzed_files=analyzed,
            skipped_files=skipped,
            total_functions=len(all_functions),
            total_lines_of_code=total_lines,
            average_cyclomatic_complexity=self._average(cyclomatic),
            maximum_cyclomatic_complexity=max(cyclomatic, default=0),
            average_cognitive_complexity=self._average(cognitive),
            maximum_cognitive_complexity=max(cognitive, default=0),
            maximum_nesting_depth=max(
                (f.max_nesting_depth for f in all_functions), default=0
            ),
            file_results=tuple(file_results),
            functions=tuple(all_functions),
        )

    def _analyze_file(self, file_path: str, source: str) -> FileComplexityResult:
        lines_of_code = sum(1 for line in source.splitlines() if line.strip())

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as exc:
            message = exc.msg or "Invalid Python syntax."
            if exc.lineno:
                message = f"Line {exc.lineno}: {message}"
            return FileComplexityResult(
                file_path=file_path,
                lines_of_code=lines_of_code,
                function_count=0,
                average_cyclomatic_complexity=0.0,
                maximum_cyclomatic_complexity=0,
                average_cognitive_complexity=0.0,
                maximum_cognitive_complexity=0,
                maximum_nesting_depth=0,
                functions=(),
                syntax_valid=False,
                syntax_error=message,
            )

        functions: list[FunctionComplexity] = []
        self._collect_functions(tree, file_path, "", functions)

        cyclomatic = [f.cyclomatic_complexity for f in functions]
        cognitive = [f.cognitive_complexity for f in functions]

        return FileComplexityResult(
            file_path=file_path,
            lines_of_code=lines_of_code,
            function_count=len(functions),
            average_cyclomatic_complexity=self._average(cyclomatic),
            maximum_cyclomatic_complexity=max(cyclomatic, default=0),
            average_cognitive_complexity=self._average(cognitive),
            maximum_cognitive_complexity=max(cognitive, default=0),
            maximum_nesting_depth=max(
                (f.max_nesting_depth for f in functions), default=0
            ),
            functions=tuple(functions),
        )

    def _collect_functions(
        self,
        node: ast.AST,
        file_path: str,
        parent_name: str,
        output: list[FunctionComplexity],
    ) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                qualified = (
                    f"{parent_name}.{child.name}" if parent_name else child.name
                )
                self._collect_functions(child, file_path, qualified, output)

            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = (
                    f"{parent_name}.{child.name}" if parent_name else child.name
                )
                output.append(self._analyze_function(file_path, child, qualified))
                # Nested functions are separately measured as their own functions.
                self._collect_functions(child, file_path, qualified, output)

    def _analyze_function(
        self,
        file_path: str,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        qualified_name: str,
    ) -> FunctionComplexity:
        end_line = getattr(node, "end_lineno", node.lineno)
        line_count = end_line - node.lineno + 1
        parameters = (
            len(node.args.posonlyargs)
            + len(node.args.args)
            + len(node.args.kwonlyargs)
            + int(node.args.vararg is not None)
            + int(node.args.kwarg is not None)
        )

        cyclomatic = self._cyclomatic_complexity(node)
        cognitive = self._cognitive_complexity(node)
        nesting = self._maximum_nesting_depth(node)

        return FunctionComplexity(
            file_path=file_path,
            name=node.name,
            qualified_name=qualified_name,
            line=node.lineno,
            end_line=end_line,
            lines=line_count,
            parameter_count=parameters,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            max_nesting_depth=nesting,
            severity=self._severity(cyclomatic, cognitive, nesting),
        )

    @staticmethod
    def _cyclomatic_complexity(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.IfExp):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += max(0, len(child.values) - 1)
            elif isinstance(child, ast.comprehension):
                complexity += len(child.ifs)
        return complexity

    @staticmethod
    def _cognitive_complexity(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> int:
        score = 0

        def visit(current: ast.AST, nesting: int) -> None:
            nonlocal score

            if isinstance(current, (ast.If, ast.For, ast.AsyncFor, ast.While)):
                score += 1 + nesting
                for child in current.body:
                    visit(child, nesting + 1)
                for child in current.orelse:
                    visit(child, nesting + (1 if isinstance(current, ast.If) else 0))
                return

            if isinstance(current, ast.Try):
                for child in current.body:
                    visit(child, nesting)
                for handler in current.handlers:
                    score += 1 + nesting
                    for child in handler.body:
                        visit(child, nesting + 1)
                for child in current.orelse + current.finalbody:
                    visit(child, nesting)
                return

            if isinstance(current, ast.IfExp):
                score += 1 + nesting
                visit(current.body, nesting + 1)
                visit(current.orelse, nesting + 1)
                visit(current.test, nesting)
                return

            if isinstance(current, ast.BoolOp):
                operators = [
                    type(operator) for operator in current.values[1:]
                ]
                previous = None
                for operator_type in operators:
                    if operator_type != previous:
                        score += 1
                    previous = operator_type

            for child in ast.iter_child_nodes(current):
                visit(child, nesting)

        for statement in node.body:
            visit(statement, 0)

        return score

    @staticmethod
    def _maximum_nesting_depth(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> int:
        maximum = 0

        def visit(current: ast.AST, depth: int) -> None:
            nonlocal maximum
            nested = isinstance(
                current,
                (
                    ast.If, ast.For, ast.AsyncFor, ast.While,
                    ast.With, ast.AsyncWith, ast.Try,
                ),
            )
            next_depth = depth + 1 if nested else depth
            maximum = max(maximum, next_depth)
            for child in ast.iter_child_nodes(current):
                visit(child, next_depth)

        for statement in node.body:
            visit(statement, 0)

        return maximum

    def _severity(
        self, cyclomatic: int, cognitive: int, nesting: int
    ) -> ComplexitySeverity:
        if (
            cyclomatic >= self.critical_cyclomatic_threshold
            or cognitive >= self.critical_cognitive_threshold
            or nesting >= self.critical_nesting_threshold
        ):
            return ComplexitySeverity.CRITICAL

        if (
            cyclomatic >= self.high_cyclomatic_threshold
            or cognitive >= self.high_cognitive_threshold
            or nesting >= self.high_nesting_threshold
        ):
            return ComplexitySeverity.HIGH

        if cyclomatic >= 5 or cognitive >= 8 or nesting >= 3:
            return ComplexitySeverity.MEDIUM

        return ComplexitySeverity.LOW

    @staticmethod
    def _average(values: list[int]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _validate_path(raw_path: object) -> str:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise CodeComplexityAnalysisError(
                "Source file paths must be non-empty strings."
            )

        normalized = raw_path.replace("\\", "/")
        parts = normalized.split("/")
        if (
            normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise CodeComplexityAnalysisError(
                f"Source path must be a normalized relative path: {raw_path}"
            )
        return normalized
