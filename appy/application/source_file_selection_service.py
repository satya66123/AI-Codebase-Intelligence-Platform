
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Iterable

class SourceFileSelectionError(ValueError):
    """Raised when source file selection fails."""

@dataclass(frozen=True)
class SourceFileSelectionResult:
    """Contains selected source files and selection statistics."""

    files: tuple
    total_files: int
    selected_count: int
    skipped_count: int
    languages: dict

class SourceFileSelectionService:
    """Select supported source-code files from repository metadata."""

    SUPPORTED_EXTENSIONS = {
        ".py": "Python",
        ".pyw": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".mjs": "JavaScript",
        ".cjs": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".c": "C",
        ".h": "C",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".hpp": "C++",
        ".cs": "C#",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".kts": "Kotlin",
        ".scala": "Scala",
        ".dart": "Dart",
        ".r": "R",
        ".sh": "Shell",
        ".bash": "Shell",
        ".sql": "SQL",
    }

    def select_source_files(
        self,
        files: Iterable,
        languages=None,
    ) -> SourceFileSelectionResult:
        """Select supported source files from file metadata."""

        if files is None:
            raise SourceFileSelectionError(
                "File metadata cannot be None."
            )

        if isinstance(files, (str, bytes, dict)):
            raise SourceFileSelectionError(
                "File metadata must be an iterable of file records."
            )

        try:
            file_records = list(files)
        except TypeError as exc:
            raise SourceFileSelectionError(
                "File metadata must be iterable."
            ) from exc

        allowed_languages = None

        if languages is not None:
            if isinstance(languages, str):
                languages = [languages]

            allowed_languages = {
                language.strip().casefold()
                for language in languages
                if isinstance(language, str) and language.strip()
            }

            if not allowed_languages:
                raise SourceFileSelectionError(
                    "At least one valid language is required."
                )

        selected_files = []
        language_counts = {}

        for record in file_records:
            file_data = self._normalize_record(record)

            extension = str(
                file_data.get("extension", "")
            ).casefold()

            if not extension:
                relative_path = file_data.get("relative_path", "")
                extension = Path(str(relative_path)).suffix.casefold()

            detected_language = self.SUPPORTED_EXTENSIONS.get(
                extension
            )

            if detected_language is None:
                continue

            if (
                allowed_languages is not None
                and detected_language.casefold()
                not in allowed_languages
            ):
                continue

            selected_files.append(record)

            language_counts[detected_language] = (
                language_counts.get(detected_language, 0) + 1
            )

        selected_count = len(selected_files)

        return SourceFileSelectionResult(
            files=tuple(selected_files),
            total_files=len(file_records),
            selected_count=selected_count,
            skipped_count=len(file_records) - selected_count,
            languages=language_counts,
        )

    @staticmethod
    def _normalize_record(record) -> dict:
        """Convert a metadata record into a dictionary."""

        if is_dataclass(record) and not isinstance(record, type):
            return asdict(record)

        if isinstance(record, dict):
            return record

        if hasattr(record, "__dict__"):
            return vars(record)

        raise SourceFileSelectionError(
            "Each file record must be a dictionary or metadata object."
        )