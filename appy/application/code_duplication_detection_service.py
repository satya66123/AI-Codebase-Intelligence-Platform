
"""Detect exact duplicated source-code blocks across repository files."""

from __future__ import annotations

import ast
import re
import tokenize
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import PurePosixPath
from typing import Mapping


class CodeDuplicationDetectionError(ValueError):
    """Raised when duplication detection receives invalid input."""


class DuplicationType(str, Enum):
    EXACT = "exact"


class DuplicationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class CodeOccurrence:
    """Location of one occurrence of duplicated code."""

    file_path: str
    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        if not isinstance(self.file_path, str) or not self.file_path.strip():
            raise ValueError("file_path must be a non-empty string.")
        if (
            isinstance(self.start_line, bool)
            or not isinstance(self.start_line, int)
            or self.start_line < 1
        ):
            raise ValueError("start_line must be a positive integer.")
        if (
            isinstance(self.end_line, bool)
            or not isinstance(self.end_line, int)
            or self.end_line < self.start_line
        ):
            raise ValueError("end_line must be >= start_line.")


@dataclass(frozen=True)
class DuplicateCodeBlock:
    """A normalized block of duplicated source code."""

    duplicate_id: str
    duplication_type: DuplicationType
    normalized_code: tuple[str, ...]
    line_count: int
    occurrences: tuple[CodeOccurrence, ...]
    severity: DuplicationSeverity

    def __post_init__(self) -> None:
        if not isinstance(self.duplicate_id, str) or not self.duplicate_id:
            raise ValueError("duplicate_id must be a non-empty string.")
        if not isinstance(self.duplication_type, DuplicationType):
            raise TypeError("duplication_type must be a DuplicationType.")
        if not isinstance(self.normalized_code, tuple):
            raise TypeError("normalized_code must be a tuple.")
        if (
            isinstance(self.line_count, bool)
            or not isinstance(self.line_count, int)
            or self.line_count < 1
        ):
            raise ValueError("line_count must be a positive integer.")
        if len(self.normalized_code) != self.line_count:
            raise ValueError("line_count must match normalized_code length.")
        if not isinstance(self.occurrences, tuple):
            raise TypeError("occurrences must be a tuple.")
        if len(self.occurrences) < 2:
            raise ValueError("A duplicate block requires at least two occurrences.")
        if not all(isinstance(item, CodeOccurrence) for item in self.occurrences):
            raise TypeError("occurrences must contain CodeOccurrence objects.")
        if not isinstance(self.severity, DuplicationSeverity):
            raise TypeError("severity must be a DuplicationSeverity.")


@dataclass(frozen=True)
class FileDuplicationResult:
    """Duplication statistics for one source file."""

    file_path: str
    total_lines: int
    duplicated_lines: int
    duplication_percentage: float
    duplicate_block_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.file_path, str) or not self.file_path:
            raise ValueError("file_path must be a non-empty string.")
        for name in (
            "total_lines",
            "duplicated_lines",
            "duplicate_block_count",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if self.duplicated_lines > self.total_lines:
            raise ValueError("duplicated_lines cannot exceed total_lines.")
        if (
            isinstance(self.duplication_percentage, bool)
            or not isinstance(self.duplication_percentage, (int, float))
            or not 0 <= self.duplication_percentage <= 100
        ):
            raise ValueError("duplication_percentage must be between 0 and 100.")


@dataclass(frozen=True)
class CodeDuplicationDetectionResult:
    """Repository-wide duplication detection statistics."""

    total_files: int
    analyzed_files: int
    skipped_files: int
    total_lines: int
    duplicated_lines: int
    duplication_percentage: float
    duplicate_block_count: int
    duplicate_blocks: tuple[DuplicateCodeBlock, ...]
    file_results: tuple[FileDuplicationResult, ...]

    def __post_init__(self) -> None:
        for name in (
            "total_files",
            "analyzed_files",
            "skipped_files",
            "total_lines",
            "duplicated_lines",
            "duplicate_block_count",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        if self.analyzed_files + self.skipped_files != self.total_files:
            raise ValueError(
                "analyzed_files and skipped_files must equal total_files."
            )
        if self.duplicated_lines > self.total_lines:
            raise ValueError("duplicated_lines cannot exceed total_lines.")
        if (
            isinstance(self.duplication_percentage, bool)
            or not isinstance(self.duplication_percentage, (int, float))
            or not 0 <= self.duplication_percentage <= 100
        ):
            raise ValueError("duplication_percentage must be between 0 and 100.")
        if not isinstance(self.duplicate_blocks, tuple):
            raise TypeError("duplicate_blocks must be a tuple.")
        if not isinstance(self.file_results, tuple):
            raise TypeError("file_results must be a tuple.")
        if not all(
            isinstance(item, DuplicateCodeBlock)
            for item in self.duplicate_blocks
        ):
            raise TypeError("duplicate_blocks must contain DuplicateCodeBlock objects.")
        if not all(
            isinstance(item, FileDuplicationResult)
            for item in self.file_results
        ):
            raise TypeError("file_results must contain FileDuplicationResult objects.")
        if self.duplicate_block_count != len(self.duplicate_blocks):
            raise ValueError("duplicate_block_count must match duplicate_blocks.")

    @property
    def has_duplicates(self) -> bool:
        return self.duplicate_block_count > 0

    @property
    def high_severity_blocks(self) -> tuple[DuplicateCodeBlock, ...]:
        return tuple(
            block
            for block in self.duplicate_blocks
            if block.severity == DuplicationSeverity.HIGH
        )


class CodeDuplicationDetectionService:
    """Detect exact normalized line-block duplication."""

    DEFAULT_MINIMUM_LINES = 5
    DEFAULT_MINIMUM_OCCURRENCES = 2
    DEFAULT_HIGH_DUPLICATE_LINES = 20
    DEFAULT_MEDIUM_DUPLICATE_LINES = 10

    SUPPORTED_EXTENSIONS = {
        ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx",
        ".java", ".c", ".h", ".cpp", ".hpp", ".cs",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt",
        ".kts", ".scala", ".sh", ".bash",
    }

    def __init__(
        self,
        minimum_lines: int = DEFAULT_MINIMUM_LINES,
        minimum_occurrences: int = DEFAULT_MINIMUM_OCCURRENCES,
        high_duplicate_lines: int = DEFAULT_HIGH_DUPLICATE_LINES,
        medium_duplicate_lines: int = DEFAULT_MEDIUM_DUPLICATE_LINES,
    ) -> None:
        values = {
            "minimum_lines": minimum_lines,
            "minimum_occurrences": minimum_occurrences,
            "high_duplicate_lines": high_duplicate_lines,
            "medium_duplicate_lines": medium_duplicate_lines,
        }

        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise CodeDuplicationDetectionError(
                    f"{name} must be a positive integer."
                )

        if high_duplicate_lines < medium_duplicate_lines:
            raise CodeDuplicationDetectionError(
                "high_duplicate_lines must be >= medium_duplicate_lines."
            )

        self.minimum_lines = minimum_lines
        self.minimum_occurrences = minimum_occurrences
        self.high_duplicate_lines = high_duplicate_lines
        self.medium_duplicate_lines = medium_duplicate_lines

    def analyze(
        self,
        source_files: Mapping[str, str],
    ) -> CodeDuplicationDetectionResult:
        """Analyze source files supplied as relative paths and source text."""
        if not isinstance(source_files, Mapping):
            raise CodeDuplicationDetectionError(
                "source_files must be a mapping of paths to source text."
            )

        normalized_files: dict[str, str] = {}

        for raw_path, content in source_files.items():
            path = self._validate_path(raw_path)

            if path in normalized_files:
                raise CodeDuplicationDetectionError(
                    f"Duplicate normalized source path: {path}"
                )

            if not isinstance(content, str):
                raise CodeDuplicationDetectionError(
                    f"Source content for '{path}' must be a string."
                )

            normalized_files[path] = content

        eligible_files = {
            path: content
            for path, content in normalized_files.items()
            if PurePosixPath(path).suffix.lower() in self.SUPPORTED_EXTENSIONS
        }

        skipped_files = len(normalized_files) - len(eligible_files)

        prepared: dict[str, list[tuple[int, str]]] = {}
        nonblank_line_numbers: dict[str, set[int]] = {}
        total_lines_by_file: dict[str, int] = {}

        for path, content in sorted(eligible_files.items()):
            prepared[path] = self._normalize_source(path, content)

            nonblank_line_numbers[path] = {
                line_number
                for line_number, line in enumerate(content.splitlines(), start=1)
                if line.strip()
            }

            total_lines_by_file[path] = len(nonblank_line_numbers[path])

        candidates = self._find_duplicate_windows(prepared)
        duplicate_blocks = self._create_duplicate_blocks(candidates)

        duplicated_line_numbers: dict[str, set[int]] = {
            path: set() for path in eligible_files
        }
        block_counts: dict[str, int] = {
            path: 0 for path in eligible_files
        }

        for block in duplicate_blocks:
            for occurrence in block.occurrences:
                block_counts[occurrence.file_path] += 1

                # Count only actual non-blank source lines inside the range.
                # The occurrence range can span blank lines removed during
                # normalization, so counting every line in range is incorrect.
                actual_lines = nonblank_line_numbers[occurrence.file_path]
                duplicated_line_numbers[occurrence.file_path].update(
                    line_number
                    for line_number in range(
                        occurrence.start_line,
                        occurrence.end_line + 1,
                    )
                    if line_number in actual_lines
                )

        total_lines = sum(total_lines_by_file.values())
        duplicated_lines = sum(
            len(line_numbers)
            for line_numbers in duplicated_line_numbers.values()
        )

        file_results = []

        for path in sorted(eligible_files):
            file_total = total_lines_by_file[path]
            file_duplicated = len(duplicated_line_numbers[path])

            file_results.append(
                FileDuplicationResult(
                    file_path=path,
                    total_lines=file_total,
                    duplicated_lines=file_duplicated,
                    duplication_percentage=self._percentage(
                        file_duplicated,
                        file_total,
                    ),
                    duplicate_block_count=block_counts[path],
                )
            )

        return CodeDuplicationDetectionResult(
            total_files=len(normalized_files),
            analyzed_files=len(eligible_files),
            skipped_files=skipped_files,
            total_lines=total_lines,
            duplicated_lines=duplicated_lines,
            duplication_percentage=self._percentage(
                duplicated_lines,
                total_lines,
            ),
            duplicate_block_count=len(duplicate_blocks),
            duplicate_blocks=duplicate_blocks,
            file_results=tuple(file_results),
        )

    def _normalize_source(
        self,
        file_path: str,
        content: str,
    ) -> list[tuple[int, str]]:
        """Return normalized non-empty lines with their original line numbers."""
        extension = PurePosixPath(file_path).suffix.lower()
        ignored_lines = (
            self._python_ignored_lines(content)
            if extension in {".py", ".pyw"}
            else set()
        )

        normalized = []

        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            if line_number in ignored_lines:
                continue

            stripped = raw_line.strip()

            if not stripped:
                continue

            if self._is_comment_only_line(extension, stripped):
                continue

            normalized_line = self._normalize_line(extension, stripped)

            if normalized_line:
                normalized.append((line_number, normalized_line))

        return normalized

    @staticmethod
    def _python_ignored_lines(content: str) -> set[int]:
        """Find Python comment lines and standalone docstring line ranges."""
        ignored: set[int] = set()

        try:
            tokens = tokenize.generate_tokens(StringIO(content).readline)

            for token in tokens:
                if token.type == tokenize.COMMENT:
                    ignored.add(token.start[0])

        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return ignored

        def collect_docstrings(body: list[ast.stmt]) -> None:
            if body:
                first = body[0]

                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    start = first.lineno
                    end = getattr(first, "end_lineno", start)
                    ignored.update(range(start, end + 1))

            for statement in body:
                if isinstance(
                    statement,
                    (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
                ):
                    collect_docstrings(statement.body)

        collect_docstrings(tree.body)
        return ignored

    @staticmethod
    def _is_comment_only_line(extension: str, line: str) -> bool:
        if extension in {".py", ".pyw", ".rb", ".sh", ".bash"}:
            return line.startswith("#")

        if extension in {
            ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".h",
            ".cpp", ".hpp", ".cs", ".go", ".rs", ".php",
            ".swift", ".kt", ".kts", ".scala",
        }:
            return (
                line.startswith("//")
                or line.startswith("/*")
                or line.startswith("*")
            )

        return False

    @staticmethod
    def _normalize_line(extension: str, line: str) -> str:
        """Normalize whitespace while retaining Python token values."""
        if extension in {".py", ".pyw"}:
            try:
                tokens = tokenize.generate_tokens(StringIO(line).readline)
                parts = []

                ignored_token_types = {
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                    tokenize.NEWLINE,
                    tokenize.NL,
                    tokenize.INDENT,
                    tokenize.DEDENT,
                    tokenize.COMMENT,
                }

                for token in tokens:
                    if token.type not in ignored_token_types:
                        parts.append(token.string)

                return " ".join(parts).strip()

            except (tokenize.TokenError, IndentationError):
                pass

        return re.sub(r"\s+", " ", line).strip()

    def _find_duplicate_windows(
        self,
        prepared: Mapping[str, list[tuple[int, str]]],
    ) -> list[
        tuple[tuple[str, ...], tuple[CodeOccurrence, ...]]
    ]:
        """Find windows shared by at least the configured occurrence count."""
        occurrences_by_window: dict[
            tuple[str, ...], list[CodeOccurrence]
        ] = {}

        for file_path, lines in prepared.items():
            if len(lines) < self.minimum_lines:
                continue

            for start_index in range(
                len(lines) - self.minimum_lines + 1
            ):
                window_entries = lines[
                    start_index:start_index + self.minimum_lines
                ]

                window = tuple(
                    normalized_line
                    for _, normalized_line in window_entries
                )

                occurrence = CodeOccurrence(
                    file_path=file_path,
                    start_line=window_entries[0][0],
                    end_line=window_entries[-1][0],
                )

                occurrences_by_window.setdefault(window, []).append(occurrence)

        return [
            (window, tuple(sorted(
                occurrences,
                key=lambda item: (
                    item.file_path,
                    item.start_line,
                    item.end_line,
                ),
            )))
            for window, occurrences in occurrences_by_window.items()
            if len(occurrences) >= self.minimum_occurrences
        ]

    def _create_duplicate_blocks(
        self,
        candidates: list[
            tuple[tuple[str, ...], tuple[CodeOccurrence, ...]]
        ],
    ) -> tuple[DuplicateCodeBlock, ...]:
        """Create deterministic findings from matching windows."""
        ordered = sorted(
            candidates,
            key=lambda item: (
                item[0],
                tuple(
                    (
                        occurrence.file_path,
                        occurrence.start_line,
                        occurrence.end_line,
                    )
                    for occurrence in item[1]
                ),
            ),
        )

        blocks = []

        for index, (window, occurrences) in enumerate(ordered, start=1):
            blocks.append(
                DuplicateCodeBlock(
                    duplicate_id=f"DUP-{index:04d}",
                    duplication_type=DuplicationType.EXACT,
                    normalized_code=window,
                    line_count=len(window),
                    occurrences=occurrences,
                    severity=self._severity(len(window)),
                )
            )

        return tuple(blocks)

    def _severity(self, line_count: int) -> DuplicationSeverity:
        if line_count >= self.high_duplicate_lines:
            return DuplicationSeverity.HIGH
        if line_count >= self.medium_duplicate_lines:
            return DuplicationSeverity.MEDIUM
        return DuplicationSeverity.LOW

    @staticmethod
    def _percentage(duplicated: int, total: int) -> float:
        if total == 0:
            return 0.0
        return round((duplicated / total) * 100.0, 2)

    @staticmethod
    def _validate_path(raw_path: object) -> str:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise CodeDuplicationDetectionError(
                "Source paths must be non-empty strings."
            )

        normalized = raw_path.replace("\\", "/")
        parts = normalized.split("/")

        if (
            normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise CodeDuplicationDetectionError(
                f"Source path must be a normalized relative path: {raw_path}"
            )

        return normalized
