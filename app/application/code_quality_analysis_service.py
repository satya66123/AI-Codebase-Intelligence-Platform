
"""Source-code quality analysis and maintainability assessment."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Mapping, Sequence


class CodeQualityAnalysisError(ValueError):
    """Raised when code quality analysis receives invalid input."""


class QualitySeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class QualityCategory(str, Enum):
    SYNTAX = "syntax"
    DOCUMENTATION = "documentation"
    NAMING = "naming"
    COMPLEXITY = "complexity"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    BEST_PRACTICE = "best_practice"


@dataclass(frozen=True)
class CodeQualityFinding:
    """One code quality finding."""

    code: str
    message: str
    file_path: str
    severity: QualitySeverity
    category: QualityCategory
    line: int | None = None
    symbol: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("Finding code must be a non-empty string.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Finding message must be a non-empty string.")
        if not isinstance(self.file_path, str) or not self.file_path.strip():
            raise ValueError("Finding file_path must be a non-empty string.")
        if not isinstance(self.severity, QualitySeverity):
            raise TypeError("severity must be a QualitySeverity.")
        if not isinstance(self.category, QualityCategory):
            raise TypeError("category must be a QualityCategory.")
        if self.line is not None and (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 1
        ):
            raise ValueError("line must be a positive integer or None.")
        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be a string.")


@dataclass(frozen=True)
class FileQualityResult:
    """Quality assessment for one source file."""

    file_path: str
    score: float
    lines_of_code: int
    findings: tuple[CodeQualityFinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.file_path, str) or not self.file_path.strip():
            raise ValueError("file_path must be a non-empty string.")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("score must be numeric.")
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100.")
        if (
            isinstance(self.lines_of_code, bool)
            or not isinstance(self.lines_of_code, int)
            or self.lines_of_code < 0
        ):
            raise ValueError("lines_of_code must be a non-negative integer.")
        if not isinstance(self.findings, tuple):
            raise TypeError("findings must be a tuple.")


@dataclass(frozen=True)
class CodeQualityAnalysisResult:
    """Repository-level code quality assessment."""

    total_files: int
    analyzed_files: int
    skipped_files: int
    total_lines_of_code: int
    score: float
    file_results: tuple[FileQualityResult, ...]
    findings: tuple[CodeQualityFinding, ...]

    def __post_init__(self) -> None:
        for name in (
            "total_files",
            "analyzed_files",
            "skipped_files",
            "total_lines_of_code",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        if self.analyzed_files + self.skipped_files != self.total_files:
            raise ValueError(
                "analyzed_files and skipped_files must equal total_files."
            )

        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("score must be numeric.")
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100.")

        if not isinstance(self.file_results, tuple):
            raise TypeError("file_results must be a tuple.")
        if not isinstance(self.findings, tuple):
            raise TypeError("findings must be a tuple.")

    @property
    def error_count(self) -> int:
        return sum(f.severity == QualitySeverity.ERROR for f in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(f.severity == QualitySeverity.WARNING for f in self.findings)

    @property
    def info_count(self) -> int:
        return sum(f.severity == QualitySeverity.INFO for f in self.findings)

    @property
    def healthy(self) -> bool:
        return self.error_count == 0

    @property
    def findings_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            key = finding.category.value
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items()))

    @property
    def findings_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            key = finding.severity.value
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items()))


class CodeQualityAnalysisService:
    """Analyze source files for common quality and maintainability issues.

    The service performs language-independent text checks and Python AST
    checks. Non-Python files receive text checks only.

    Input:
        source_files: mapping of repository-relative file paths to source text.

    Optional entities:
        Existing CodeEntity-like objects may be supplied. The service reads
        their documented fields when available, but does not mutate them.
    """

    DEFAULT_MAX_LINE_LENGTH = 100
    DEFAULT_MAX_FUNCTION_LINES = 50
    DEFAULT_MAX_CLASS_LINES = 300
    DEFAULT_MAX_FUNCTION_PARAMETERS = 5
    DEFAULT_MAX_COMPLEXITY = 10

    SUPPORTED_PYTHON_EXTENSIONS = {".py", ".pyw"}

    def __init__(
        self,
        max_line_length: int = DEFAULT_MAX_LINE_LENGTH,
        max_function_lines: int = DEFAULT_MAX_FUNCTION_LINES,
        max_class_lines: int = DEFAULT_MAX_CLASS_LINES,
        max_function_parameters: int = DEFAULT_MAX_FUNCTION_PARAMETERS,
        max_complexity: int = DEFAULT_MAX_COMPLEXITY,
    ) -> None:
        limits = {
            "max_line_length": max_line_length,
            "max_function_lines": max_function_lines,
            "max_class_lines": max_class_lines,
            "max_function_parameters": max_function_parameters,
            "max_complexity": max_complexity,
        }

        for name, value in limits.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise CodeQualityAnalysisError(
                    f"{name} must be a positive integer."
                )

        self.max_line_length = max_line_length
        self.max_function_lines = max_function_lines
        self.max_class_lines = max_class_lines
        self.max_function_parameters = max_function_parameters
        self.max_complexity = max_complexity

    def analyze(
        self,
        source_files: Mapping[str, str],
        entities: Sequence[object] | None = None,
    ) -> CodeQualityAnalysisResult:
        """Analyze a mapping of relative source paths to source contents."""
        if not isinstance(source_files, Mapping):
            raise CodeQualityAnalysisError(
                "source_files must be a mapping of paths to source text."
            )

        if entities is not None and (
            isinstance(entities, (str, bytes))
            or not isinstance(entities, Sequence)
        ):
            raise CodeQualityAnalysisError(
                "entities must be a sequence or None."
            )

        normalized_files: list[tuple[str, str]] = []
        seen_paths: set[str] = set()

        for raw_path, content in source_files.items():
            path = self._validate_path(raw_path)
            if path in seen_paths:
                raise CodeQualityAnalysisError(
                    f"Duplicate normalized source path: {path}"
                )
            seen_paths.add(path)

            if not isinstance(content, str):
                raise CodeQualityAnalysisError(
                    f"Source content for '{path}' must be a string."
                )

            normalized_files.append((path, content))

        normalized_files.sort(key=lambda item: item[0])

        file_results: list[FileQualityResult] = []
        all_findings: list[CodeQualityFinding] = []
        total_lines = 0
        analyzed_files = 0
        skipped_files = 0

        for file_path, content in normalized_files:
            extension = PurePosixPath(file_path).suffix.lower()

            if extension not in self.SUPPORTED_PYTHON_EXTENSIONS:
                skipped_files += 1
                continue

            analyzed_files += 1
            file_result = self._analyze_python_file(file_path, content)
            file_results.append(file_result)
            all_findings.extend(file_result.findings)
            total_lines += file_result.lines_of_code

        repository_score = self._calculate_score(all_findings, analyzed_files)

        return CodeQualityAnalysisResult(
            total_files=len(normalized_files),
            analyzed_files=analyzed_files,
            skipped_files=skipped_files,
            total_lines_of_code=total_lines,
            score=repository_score,
            file_results=tuple(file_results),
            findings=tuple(all_findings),
        )

    def _analyze_python_file(
        self, file_path: str, content: str
    ) -> FileQualityResult:
        findings: list[CodeQualityFinding] = []
        lines = content.splitlines()
        lines_of_code = sum(1 for line in lines if line.strip())

        self._check_text_quality(file_path, lines, findings)

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as exc:
            findings.append(
                CodeQualityFinding(
                    code="PYTHON_SYNTAX_ERROR",
                    message=exc.msg or "Invalid Python syntax.",
                    file_path=file_path,
                    severity=QualitySeverity.ERROR,
                    category=QualityCategory.SYNTAX,
                    line=exc.lineno,
                )
            )
            score = self._calculate_score(findings, 1)
            return FileQualityResult(
                file_path=file_path,
                score=score,
                lines_of_code=lines_of_code,
                findings=tuple(findings),
            )

        self._check_ast_quality(file_path, tree, findings)

        score = self._calculate_score(findings, 1)
        return FileQualityResult(
            file_path=file_path,
            score=score,
            lines_of_code=lines_of_code,
            findings=tuple(findings),
        )

    def _check_text_quality(
        self,
        file_path: str,
        lines: list[str],
        findings: list[CodeQualityFinding],
    ) -> None:
        for line_number, line in enumerate(lines, start=1):
            if len(line) > self.max_line_length:
                findings.append(
                    CodeQualityFinding(
                        code="LINE_TOO_LONG",
                        message=(
                            f"Line contains {len(line)} characters; "
                            f"maximum is {self.max_line_length}."
                        ),
                        file_path=file_path,
                        severity=QualitySeverity.WARNING,
                        category=QualityCategory.STYLE,
                        line=line_number,
                    )
                )

            if line.rstrip(" \t") != line:
                findings.append(
                    CodeQualityFinding(
                        code="TRAILING_WHITESPACE",
                        message="Line contains trailing whitespace.",
                        file_path=file_path,
                        severity=QualitySeverity.INFO,
                        category=QualityCategory.STYLE,
                        line=line_number,
                    )
                )

            if "\t" in line:
                findings.append(
                    CodeQualityFinding(
                        code="TAB_INDENTATION",
                        message="Line contains tab characters.",
                        file_path=file_path,
                        severity=QualitySeverity.INFO,
                        category=QualityCategory.STYLE,
                        line=line_number,
                    )
                )

            if re.search(r"\bTODO\b|\bFIXME\b|\bXXX\b", line):
                findings.append(
                    CodeQualityFinding(
                        code="DEVELOPMENT_MARKER",
                        message="Source contains a TODO, FIXME, or XXX marker.",
                        file_path=file_path,
                        severity=QualitySeverity.INFO,
                        category=QualityCategory.MAINTAINABILITY,
                        line=line_number,
                    )
                )

    def _check_ast_quality(
        self,
        file_path: str,
        tree: ast.AST,
        findings: list[CodeQualityFinding],
    ) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_function(file_path, node, findings)

            elif isinstance(node, ast.ClassDef):
                self._check_class(file_path, node, findings)

            elif isinstance(node, ast.ExceptHandler):
                self._check_exception_handler(file_path, node, findings)

        self._check_module_docstring(file_path, tree, findings)

    def _check_function(
        self,
        file_path: str,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        findings: list[CodeQualityFinding],
    ) -> None:
        name = node.name
        line = node.lineno
        end_line = getattr(node, "end_lineno", line)
        function_lines = end_line - line + 1

        if not ast.get_docstring(node):
            findings.append(
                CodeQualityFinding(
                    code="MISSING_FUNCTION_DOCSTRING",
                    message=f"Function '{name}' has no docstring.",
                    file_path=file_path,
                    severity=QualitySeverity.INFO,
                    category=QualityCategory.DOCUMENTATION,
                    line=line,
                    symbol=name,
                )
            )

        if function_lines > self.max_function_lines:
            findings.append(
                CodeQualityFinding(
                    code="FUNCTION_TOO_LONG",
                    message=(
                        f"Function '{name}' spans {function_lines} lines; "
                        f"maximum is {self.max_function_lines}."
                    ),
                    file_path=file_path,
                    severity=QualitySeverity.WARNING,
                    category=QualityCategory.COMPLEXITY,
                    line=line,
                    symbol=name,
                )
            )

        parameters = (
            len(node.args.posonlyargs)
            + len(node.args.args)
            + len(node.args.kwonlyargs)
        )
        if node.args.vararg is not None:
            parameters += 1
        if node.args.kwarg is not None:
            parameters += 1

        if parameters > self.max_function_parameters:
            findings.append(
                CodeQualityFinding(
                    code="TOO_MANY_PARAMETERS",
                    message=(
                        f"Function '{name}' has {parameters} parameters; "
                        f"maximum is {self.max_function_parameters}."
                    ),
                    file_path=file_path,
                    severity=QualitySeverity.WARNING,
                    category=QualityCategory.COMPLEXITY,
                    line=line,
                    symbol=name,
                )
            )

        complexity = self._calculate_cyclomatic_complexity(node)
        if complexity > self.max_complexity:
            findings.append(
                CodeQualityFinding(
                    code="HIGH_CYCLOMATIC_COMPLEXITY",
                    message=(
                        f"Function '{name}' has estimated cyclomatic "
                        f"complexity {complexity}; maximum is "
                        f"{self.max_complexity}."
                    ),
                    file_path=file_path,
                    severity=QualitySeverity.WARNING,
                    category=QualityCategory.COMPLEXITY,
                    line=line,
                    symbol=name,
                )
            )

        if not name.startswith("_") and not re.fullmatch(
            r"[a-z][a-z0-9_]*", name
        ):
            findings.append(
                CodeQualityFinding(
                    code="FUNCTION_NAMING_CONVENTION",
                    message=(
                        f"Function '{name}' does not follow "
                        "lowercase_with_underscores naming."
                    ),
                    file_path=file_path,
                    severity=QualitySeverity.INFO,
                    category=QualityCategory.NAMING,
                    line=line,
                    symbol=name,
                )
            )

    def _check_class(
        self,
        file_path: str,
        node: ast.ClassDef,
        findings: list[CodeQualityFinding],
    ) -> None:
        name = node.name
        line = node.lineno
        end_line = getattr(node, "end_lineno", line)
        class_lines = end_line - line + 1

        if not ast.get_docstring(node):
            findings.append(
                CodeQualityFinding(
                    code="MISSING_CLASS_DOCSTRING",
                    message=f"Class '{name}' has no docstring.",
                    file_path=file_path,
                    severity=QualitySeverity.INFO,
                    category=QualityCategory.DOCUMENTATION,
                    line=line,
                    symbol=name,
                )
            )

        if class_lines > self.max_class_lines:
            findings.append(
                CodeQualityFinding(
                    code="CLASS_TOO_LONG",
                    message=(
                        f"Class '{name}' spans {class_lines} lines; "
                        f"maximum is {self.max_class_lines}."
                    ),
                    file_path=file_path,
                    severity=QualitySeverity.WARNING,
                    category=QualityCategory.MAINTAINABILITY,
                    line=line,
                    symbol=name,
                )
            )

        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", name):
            findings.append(
                CodeQualityFinding(
                    code="CLASS_NAMING_CONVENTION",
                    message=(
                        f"Class '{name}' does not follow PascalCase naming."
                    ),
                    file_path=file_path,
                    severity=QualitySeverity.INFO,
                    category=QualityCategory.NAMING,
                    line=line,
                    symbol=name,
                )
            )

    def _check_exception_handler(
        self,
        file_path: str,
        node: ast.ExceptHandler,
        findings: list[CodeQualityFinding],
    ) -> None:
        catches_all = node.type is None or (
            isinstance(node.type, ast.Name) and node.type.id == "Exception"
        )

        if catches_all:
            findings.append(
                CodeQualityFinding(
                    code="BROAD_EXCEPTION_HANDLER",
                    message=(
                        "Broad exception handling may hide unexpected errors."
                    ),
                    file_path=file_path,
                    severity=QualitySeverity.WARNING,
                    category=QualityCategory.BEST_PRACTICE,
                    line=node.lineno,
                )
            )

        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            findings.append(
                CodeQualityFinding(
                    code="EMPTY_EXCEPTION_HANDLER",
                    message="Exception handler silently ignores the exception.",
                    file_path=file_path,
                    severity=QualitySeverity.WARNING,
                    category=QualityCategory.BEST_PRACTICE,
                    line=node.lineno,
                )
            )

    @staticmethod
    def _check_module_docstring(
        file_path: str,
        tree: ast.AST,
        findings: list[CodeQualityFinding],
    ) -> None:
        if not isinstance(tree, ast.Module):
            return

        if not ast.get_docstring(tree):
            findings.append(
                CodeQualityFinding(
                    code="MISSING_MODULE_DOCSTRING",
                    message="Python module has no module-level docstring.",
                    file_path=file_path,
                    severity=QualitySeverity.INFO,
                    category=QualityCategory.DOCUMENTATION,
                    line=1,
                )
            )

    @staticmethod
    def _calculate_cyclomatic_complexity(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> int:
        """Return a simple cyclomatic complexity estimate."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += max(0, len(child.values) - 1)
            elif isinstance(child, ast.IfExp):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += len(child.ifs)

        return complexity

    @staticmethod
    def _calculate_score(
        findings: Sequence[CodeQualityFinding],
        analyzed_files: int,
    ) -> float:
        if analyzed_files == 0:
            return 100.0

        deductions = {
            QualitySeverity.ERROR: 10.0,
            QualitySeverity.WARNING: 3.0,
            QualitySeverity.INFO: 0.5,
        }

        penalty = sum(deductions[item.severity] for item in findings)
        return round(max(0.0, 100.0 - penalty / analyzed_files), 2)

    @staticmethod
    def _validate_path(raw_path: object) -> str:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise CodeQualityAnalysisError(
                "Source file paths must be non-empty strings."
            )

        normalized = raw_path.replace("\\", "/")
        parts = normalized.split("/")

        if (
            normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise CodeQualityAnalysisError(
                f"Source path must be a normalized relative path: {raw_path}"
            )

        return normalized
