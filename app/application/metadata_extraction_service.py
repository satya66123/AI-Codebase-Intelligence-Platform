
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.application.repository_scanner import RepositoryScanResult
from app.application.language_detection_service import (
    LanguageDetectionService,
)


class MetadataExtractionError(ValueError):
    """Raised when metadata extraction fails."""


@dataclass(frozen=True)
class FileMetadata:
    name: str
    relative_path: str
    extension: str
    language: str
    size_bytes: int
    modified_time: str


class MetadataExtractionService:
    """Extracts file and repository metadata."""

    def __init__(self, language_service=None):
        self.language_service = (
            language_service or LanguageDetectionService()
        )

    def extract_file_metadata(
        self,
        file_path: Path,
        repository_root: Path,
    ) -> FileMetadata:
        """Extract metadata for an individual repository file."""

        file_path = Path(file_path)
        repository_root = Path(repository_root)

        try:
            relative_path = file_path.relative_to(repository_root)
        except ValueError as exc:
            raise MetadataExtractionError(
                "File is outside the repository root."
            ) from exc

        if not file_path.is_file():
            raise MetadataExtractionError(
                "Metadata can only be extracted from existing files."
            )

        try:
            file_stats = file_path.stat()
        except OSError as exc:
            raise MetadataExtractionError(
                f"Unable to read file metadata: {file_path}"
            ) from exc

        return FileMetadata(
            name=file_path.name,
            relative_path=relative_path.as_posix(),
            extension=file_path.suffix.lower(),
            language=self.language_service.detect_language(
                file_path
            ),
            size_bytes=file_stats.st_size,
            modified_time=datetime.fromtimestamp(
                file_stats.st_mtime
            ).isoformat(),
        )

    def extract_repository_metadata(
        self,
        result: RepositoryScanResult,
    ) -> dict:
        """Extract metadata and aggregate repository statistics."""

        if not isinstance(result, RepositoryScanResult):
            raise MetadataExtractionError(
                "A valid RepositoryScanResult object is required."
            )

        file_metadata = []

        for file_path in result.files:
            file_metadata.append(
                self.extract_file_metadata(
                    file_path,
                    result.root,
                )
            )

        language_counts = {}

        for metadata in file_metadata:
            language = metadata.language

            language_counts[language] = (
                language_counts.get(language, 0) + 1
            )

        total_size = sum(
            metadata.size_bytes
            for metadata in file_metadata
        )

        return {
            "repository_name": result.root.name,
            "repository_path": str(result.root),
            "total_files": len(file_metadata),
            "total_directories": result.total_directories,
            "total_symlinks": result.total_symlinks,
            "total_size_bytes": total_size,
            "languages": dict(sorted(language_counts.items())),
            "files": file_metadata,
        }
