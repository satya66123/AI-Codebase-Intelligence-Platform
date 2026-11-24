
from dataclasses import replace
from fnmatch import fnmatchcase
from pathlib import Path

from app.application.repository_scanner import RepositoryScanResult


class IgnoreRuleError(ValueError):
    """Raised when ignore-rule processing fails."""


class IgnoreRuleService:
    """Filters repository entries using default, custom and .gitignore rules."""

    DEFAULT_IGNORED_DIRECTORIES = (
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "build",
        "dist",
    )

    DEFAULT_IGNORED_FILES = (
        "*.pyc",
        "*.pyo",
        ".DS_Store",
        "Thumbs.db",
    )

    def filter_scan_result(
        self,
        result: RepositoryScanResult,
        ignored_directories=None,
        ignored_files=None,
        respect_gitignore: bool = True,
    ) -> RepositoryScanResult:
        if not isinstance(result, RepositoryScanResult):
            raise IgnoreRuleError(
                "A valid RepositoryScanResult object is required."
            )

        directory_patterns = (
            self.DEFAULT_IGNORED_DIRECTORIES
            + tuple(ignored_directories or ())
        )
        file_patterns = (
            self.DEFAULT_IGNORED_FILES
            + tuple(ignored_files or ())
        )

        if not all(isinstance(p, str) and p.strip()
                   for p in directory_patterns + file_patterns):
            raise IgnoreRuleError(
                "Ignore patterns must be non-empty strings."
            )

        gitignore_rules = []

        if respect_gitignore:
            gitignore_path = result.root / ".gitignore"

            try:
                if gitignore_path.is_file():
                    gitignore_rules = self._read_gitignore(
                        gitignore_path
                    )
            except OSError as exc:
                raise IgnoreRuleError(
                    "Unable to read .gitignore."
                ) from exc

        def is_ignored(path: Path, is_directory: bool) -> bool:
            try:
                relative_path = path.relative_to(result.root)
            except ValueError as exc:
                raise IgnoreRuleError(
                    "Repository entry exists outside the repository root."
                ) from exc

            parts = relative_path.parts

            # Check the entry and each parent directory.
            for index in range(1, len(parts) + 1):
                candidate_parts = parts[:index]
                candidate = Path(*candidate_parts)
                candidate_is_directory = (
                    index < len(parts) or is_directory
                )

                # Default and custom directory rules.
                if any(
                    fnmatchcase(part, pattern)
                    for part in candidate_parts
                    for pattern in directory_patterns
                ):
                    return True

                # File rules apply to the entry itself.
                if (
                    index == len(parts)
                    and not is_directory
                    and any(
                        fnmatchcase(candidate.name, pattern)
                        for pattern in file_patterns
                    )
                ):
                    return True

                # Evaluate .gitignore rules in their declared order.
                ignored = False

                for pattern, negated, directory_only in gitignore_rules:
                    if directory_only and not candidate_is_directory:
                        continue

                    if self._matches_gitignore_pattern(
                        candidate,
                        pattern
                    ):
                        ignored = not negated

                if ignored:
                    return True

            return False

        filtered_directories = tuple(
            path
            for path in result.directories
            if not is_ignored(path, is_directory=True)
        )

        filtered_files = tuple(
            path
            for path in result.files
            if not is_ignored(path, is_directory=False)
        )

        filtered_symlinks = tuple(
            path
            for path in result.symlinks
            if not is_ignored(path, is_directory=False)
        )

        return replace(
            result,
            files=filtered_files,
            directories=filtered_directories,
            symlinks=filtered_symlinks,
        )

    @staticmethod
    def _read_gitignore(path: Path) -> list:
        rules = []

        for raw_line in path.read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            negated = line.startswith("!")
            if negated:
                line = line[1:]

            line = line.lstrip("/")
            directory_only = line.endswith("/")
            line = line.rstrip("/")

            if line:
                rules.append((line, negated, directory_only))

        return rules

    @staticmethod
    def _matches_gitignore_pattern(
        candidate: Path,
        pattern: str
    ) -> bool:
        candidate_text = candidate.as_posix()

        if "/" in pattern:
            return fnmatchcase(candidate_text, pattern)

        return fnmatchcase(candidate.name, pattern)
