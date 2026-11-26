
"""Conservative static dead-code detection for Python source files."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Mapping


class DeadCodeDetectionError(ValueError):
    """Raised when dead-code detection receives invalid input."""


class DeadCodeType(str, Enum):
    UNUSED_FUNCTION = "unused_function"
    UNUSED_CLASS = "unused_class"
    UNUSED_IMPORT = "unused_import"
    UNREACHABLE_CODE = "unreachable_code"


class DeadCodeSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class DeadCodeFinding:
    """One potential dead-code finding."""

    file_path: str
    line: int
    end_line: int
    code_type: DeadCodeType
    severity: DeadCodeSeverity
    symbol: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.file_path, str) or not self.file_path:
            raise ValueError("file_path must be a non-empty string.")
        if (
            isinstance(self.line, bool)
            or not isinstance(self.line, int)
            or self.line < 1
        ):
            raise ValueError("line must be a positive integer.")
        if (
            isinstance(self.end_line, bool)
            or not isinstance(self.end_line, int)
            or self.end_line < self.line
        ):
            raise ValueError("end_line must be >= line.")
        if not isinstance(self.code_type, DeadCodeType):
            raise TypeError("code_type must be a DeadCodeType.")
        if not isinstance(self.severity, DeadCodeSeverity):
            raise TypeError("severity must be a DeadCodeSeverity.")
        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be a string.")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("message must be a non-empty string.")


@dataclass(frozen=True)
class DeadCodeFileResult:
    """Dead-code analysis result for one Python file."""

    file_path: str
    total_lines: int
    analyzed: bool
    syntax_error: str
    findings: tuple[DeadCodeFinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.file_path, str) or not self.file_path:
            raise ValueError("file_path must be a non-empty string.")
        if (
            isinstance(self.total_lines, bool)
            or not isinstance(self.total_lines, int)
            or self.total_lines < 0
        ):
            raise ValueError("total_lines must be a non-negative integer.")
        if not isinstance(self.analyzed, bool):
            raise TypeError("analyzed must be a boolean.")
        if not isinstance(self.syntax_error, str):
            raise TypeError("syntax_error must be a string.")
        if not isinstance(self.findings, tuple):
            raise TypeError("findings must be a tuple.")
        if not all(isinstance(item, DeadCodeFinding) for item in self.findings):
            raise TypeError("findings must contain DeadCodeFinding objects.")
        if self.analyzed and self.syntax_error:
            raise ValueError("An analyzed file cannot have a syntax error.")
        if not self.analyzed and not self.syntax_error:
            raise ValueError("A non-analyzed file must provide a syntax error.")


@dataclass(frozen=True)
class DeadCodeDetectionResult:
    """Repository-wide dead-code analysis result."""

    total_files: int
    analyzed_files: int
    skipped_files: int
    total_findings: int
    findings: tuple[DeadCodeFinding, ...]
    file_results: tuple[DeadCodeFileResult, ...]

    def __post_init__(self) -> None:
        for name in (
            "total_files",
            "analyzed_files",
            "skipped_files",
            "total_findings",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        if self.analyzed_files + self.skipped_files != self.total_files:
            raise ValueError(
                "analyzed_files and skipped_files must equal total_files."
            )
        if not isinstance(self.findings, tuple):
            raise TypeError("findings must be a tuple.")
        if not isinstance(self.file_results, tuple):
            raise TypeError("file_results must be a tuple.")
        if not all(isinstance(item, DeadCodeFinding) for item in self.findings):
            raise TypeError("findings must contain DeadCodeFinding objects.")
        if not all(
            isinstance(item, DeadCodeFileResult) for item in self.file_results
        ):
            raise TypeError("file_results must contain DeadCodeFileResult objects.")
        if self.total_findings != len(self.findings):
            raise ValueError("total_findings must match findings length.")

    @property
    def has_dead_code(self) -> bool:
        return self.total_findings > 0

    @property
    def high_severity_findings(self) -> tuple[DeadCodeFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity == DeadCodeSeverity.HIGH
        )

    @property
    def findings_by_type(self) -> dict[DeadCodeType, int]:
        counts = {item: 0 for item in DeadCodeType}
        for finding in self.findings:
            counts[finding.code_type] += 1
        return counts

    @property
    def syntax_error_count(self) -> int:
        return sum(
            1 for result in self.file_results if not result.analyzed
        )


class DeadCodeDetectionService:
    """Detect selected categories of potential dead code in Python files.

    The detector intentionally uses conservative rules:
    - Only private module-level functions and classes are checked for
      unreferenced definitions by default.
    - Imports are checked using loaded identifier names.
    - Statements following unconditional terminators are reported as
      unreachable within their immediate statement block.
    - Unsupported languages are skipped.
    """

    PYTHON_EXTENSIONS = {".py", ".pyw"}

    def __init__(
        self,
        include_public_symbols: bool = False,
        detect_unused_imports: bool = True,
        detect_unreachable_code: bool = True,
    ) -> None:
        for name, value in (
            ("include_public_symbols", include_public_symbols),
            ("detect_unused_imports", detect_unused_imports),
            ("detect_unreachable_code", detect_unreachable_code),
        ):
            if not isinstance(value, bool):
                raise DeadCodeDetectionError(f"{name} must be a boolean.")

        self.include_public_symbols = include_public_symbols
        self.detect_unused_imports = detect_unused_imports
        self.detect_unreachable_code = detect_unreachable_code

    def analyze(
        self,
        source_files: Mapping[str, str],
    ) -> DeadCodeDetectionResult:
        """Analyze a mapping of relative file paths to source text."""
        if not isinstance(source_files, Mapping):
            raise DeadCodeDetectionError(
                "source_files must be a mapping of paths to source text."
            )

        normalized_files: dict[str, str] = {}

        for raw_path, content in source_files.items():
            path = self._validate_path(raw_path)

            if path in normalized_files:
                raise DeadCodeDetectionError(
                    f"Duplicate normalized source path: {path}"
                )
            if not isinstance(content, str):
                raise DeadCodeDetectionError(
                    f"Source content for '{path}' must be a string."
                )

            normalized_files[path] = content

        python_files = {
            path: content
            for path, content in normalized_files.items()
            if PurePosixPath(path).suffix.lower() in self.PYTHON_EXTENSIONS
        }

        file_results: list[DeadCodeFileResult] = []

        for path, content in sorted(python_files.items()):
            file_results.append(self._analyze_file(path, content))

        all_findings = tuple(
            finding
            for result in file_results
            for finding in result.findings
        )

        return DeadCodeDetectionResult(
            total_files=len(normalized_files),
            analyzed_files=len(file_results),
            skipped_files=len(normalized_files) - len(python_files),
            total_findings=len(all_findings),
            findings=all_findings,
            file_results=tuple(file_results),
        )

    def _analyze_file(
        self,
        file_path: str,
        source: str,
    ) -> DeadCodeFileResult:
        total_lines = len(source.splitlines())

        try:
            tree = ast.parse(source, filename=file_path)
        except (SyntaxError, ValueError, TypeError) as exc:
            return DeadCodeFileResult(
                file_path=file_path,
                total_lines=total_lines,
                analyzed=False,
                syntax_error=str(exc),
                findings=(),
            )

        findings: list[DeadCodeFinding] = []

        loaded_names = self._collect_loaded_names(tree)
        exported_names = self._collect_exported_names(tree)

        findings.extend(
            self._find_unused_definitions(
                file_path,
                tree,
                loaded_names,
                exported_names,
            )
        )

        if self.detect_unused_imports:
            findings.extend(
                self._find_unused_imports(file_path, tree, loaded_names)
            )

        if self.detect_unreachable_code:
            findings.extend(
                self._find_unreachable_code(file_path, tree)
            )

        findings.sort(
            key=lambda item: (
                item.line,
                item.end_line,
                item.code_type.value,
                item.symbol,
            )
        )

        return DeadCodeFileResult(
            file_path=file_path,
            total_lines=total_lines,
            analyzed=True,
            syntax_error="",
            findings=tuple(findings),
        )

    @staticmethod
    def _collect_loaded_names(tree: ast.AST) -> set[str]:
        return {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }

    @staticmethod
    def _collect_exported_names(tree: ast.Module) -> set[str]:
        """Read literal names declared through module-level __all__."""
        exported: set[str] = set()

        for statement in tree.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue

            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )

            if not any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in targets
            ):
                continue

            value = statement.value
            if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                for element in value.elts:
                    if (
                        isinstance(element, ast.Constant)
                        and isinstance(element.value, str)
                    ):
                        exported.add(element.value)

        return exported

    def _find_unused_definitions(
        self,
        file_path: str,
        tree: ast.Module,
        loaded_names: set[str],
        exported_names: set[str],
    ) -> list[DeadCodeFinding]:
        findings = []

        for node in tree.body:
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                continue

            name = node.name

            if name in exported_names:
                continue

            if not self.include_public_symbols and not name.startswith("_"):
                continue

            if name.startswith("__") and name.endswith("__"):
                continue

            if name in loaded_names:
                continue

            is_class = isinstance(node, ast.ClassDef)
            code_type = (
                DeadCodeType.UNUSED_CLASS
                if is_class
                else DeadCodeType.UNUSED_FUNCTION
            )
            symbol_type = "class" if is_class else "function"

            findings.append(
                DeadCodeFinding(
                    file_path=file_path,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    code_type=code_type,
                    severity=DeadCodeSeverity.MEDIUM,
                    symbol=name,
                    message=(
                        f"Private module-level {symbol_type} '{name}' "
                        "has no detected reference in this file."
                    ),
                )
            )

        return findings

    @staticmethod
    def _find_unused_imports(
        file_path: str,
        tree: ast.Module,
        loaded_names: set[str],
    ) -> list[DeadCodeFinding]:
        findings = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            # Future imports configure compiler behavior and are not treated
            # as ordinary unused imports.
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue

            for alias in node.names:
                if alias.name == "*":
                    continue

                bound_name = alias.asname or alias.name.split(".")[0]

                if bound_name in loaded_names:
                    continue

                imported_name = alias.name

                findings.append(
                    DeadCodeFinding(
                        file_path=file_path,
                        line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        code_type=DeadCodeType.UNUSED_IMPORT,
                        severity=DeadCodeSeverity.LOW,
                        symbol=bound_name,
                        message=(
                            f"Imported name '{imported_name}' "
                            "has no detected usage in this file."
                        ),
                    )
                )

        return findings

    def _find_unreachable_code(
        self,
        file_path: str,
        tree: ast.Module,
    ) -> list[DeadCodeFinding]:
        findings: list[DeadCodeFinding] = []

        for node in ast.walk(tree):
            for statements in self._statement_bodies(node):
                terminated = False

                for statement in statements:
                    if terminated:
                        findings.append(
                            DeadCodeFinding(
                                file_path=file_path,
                                line=statement.lineno,
                                end_line=getattr(
                                    statement,
                                    "end_lineno",
                                    statement.lineno,
                                ),
                                code_type=DeadCodeType.UNREACHABLE_CODE,
                                severity=DeadCodeSeverity.HIGH,
                                symbol=type(statement).__name__,
                                message=(
                                    "Statement is unreachable because an "
                                    "earlier statement unconditionally "
                                    "terminates this block."
                                ),
                            )
                        )
                    elif self._always_terminates(statement):
                        terminated = True

        return findings

    @staticmethod
    def _statement_bodies(node: ast.AST) -> list[list[ast.stmt]]:
        """Return immediate statement lists owned by a node."""
        bodies: list[list[ast.stmt]] = []

        for attribute in ("body", "orelse", "finalbody"):
            value = getattr(node, attribute, None)
            if isinstance(value, list) and value and all(
                isinstance(item, ast.stmt) for item in value
            ):
                bodies.append(value)

        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.body:
                    bodies.append(handler.body)

        if isinstance(node, ast.Match):
            for case in node.cases:
                if case.body:
                    bodies.append(case.body)

        return bodies

    def _always_terminates(self, node: ast.stmt) -> bool:
        if isinstance(
            node,
            (ast.Return, ast.Raise, ast.Break, ast.Continue),
        ):
            return True

        if isinstance(node, ast.If):
            return bool(node.orelse) and (
                self._block_terminates(node.body)
                and self._block_terminates(node.orelse)
            )

        return False

    def _block_terminates(self, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if self._always_terminates(statement):
                return True
        return False

    @staticmethod
    def _validate_path(raw_path: object) -> str:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise DeadCodeDetectionError(
                "Source paths must be non-empty strings."
            )

        normalized = raw_path.replace("\\", "/")
        parts = normalized.split("/")

        if (
            normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise DeadCodeDetectionError(
                f"Source path must be a normalized relative path: {raw_path}"
            )

        return normalized
