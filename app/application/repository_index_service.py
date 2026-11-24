
from dataclasses import asdict

from app.application.metadata_extraction_service import (
    FileMetadata,
)


class RepositoryIndexError(ValueError):
    """Raised when repository indexing fails."""


class RepositoryIndexService:
    """Builds and searches a metadata-based repository index."""

    def build_index(self, repository_metadata: dict) -> dict:
        """Build a searchable index from extracted repository metadata."""

        if not isinstance(repository_metadata, dict):
            raise RepositoryIndexError(
                "Repository metadata must be a dictionary."
            )

        required_fields = {
            "repository_name",
            "repository_path",
            "total_files",
            "total_directories",
            "total_size_bytes",
            "languages",
            "files",
        }

        missing_fields = required_fields - repository_metadata.keys()

        if missing_fields:
            raise RepositoryIndexError(
                f"Missing repository metadata fields: "
                f"{', '.join(sorted(missing_fields))}"
            )

        if not isinstance(repository_metadata["files"], list):
            raise RepositoryIndexError(
                "Repository files metadata must be a list."
            )

        indexed_files = []

        for metadata in repository_metadata["files"]:
            if isinstance(metadata, FileMetadata):
                indexed_files.append(asdict(metadata))

            elif isinstance(metadata, dict):
                required_file_fields = {
                    "name",
                    "relative_path",
                    "extension",
                    "language",
                    "size_bytes",
                    "modified_time",
                }

                if not required_file_fields.issubset(metadata):
                    raise RepositoryIndexError(
                        "File metadata contains missing fields."
                    )

                indexed_files.append(dict(metadata))

            else:
                raise RepositoryIndexError(
                    "Each file entry must be FileMetadata or a dictionary."
                )

        return {
            "repository_name": repository_metadata["repository_name"],
            "repository_path": repository_metadata["repository_path"],
            "total_files": len(indexed_files),
            "total_directories": repository_metadata["total_directories"],
            "total_size_bytes": repository_metadata["total_size_bytes"],
            "languages": dict(repository_metadata["languages"]),
            "files": indexed_files,
        }

    def search_files(self, index: dict, query: str) -> list:
        """Search indexed files by name, path, extension, or language."""

        self._validate_index(index)

        if not isinstance(query, str) or not query.strip():
            raise RepositoryIndexError(
                "Search query must be a non-empty string."
            )

        search_term = query.strip().casefold()

        return [
            file_metadata
            for file_metadata in index["files"]
            if any(
                search_term in str(file_metadata[field]).casefold()
                for field in (
                    "name",
                    "relative_path",
                    "extension",
                    "language",
                )
            )
        ]

    def get_file(self, index: dict, relative_path: str):
        """Retrieve file metadata using its repository-relative path."""

        self._validate_index(index)

        if not isinstance(relative_path, str) or not relative_path.strip():
            raise RepositoryIndexError(
                "Relative file path must be a non-empty string."
            )

        normalized_path = relative_path.replace("\\", "/").casefold()

        for file_metadata in index["files"]:
            indexed_path = file_metadata["relative_path"].replace(
                "\\", "/"
            ).casefold()

            if indexed_path == normalized_path:
                return file_metadata

        return None

    def get_language_files(self, index: dict, language: str) -> list:
        """Return indexed files belonging to a programming language."""

        self._validate_index(index)

        if not isinstance(language, str) or not language.strip():
            raise RepositoryIndexError(
                "Language must be a non-empty string."
            )

        language = language.strip().casefold()

        return [
            file_metadata
            for file_metadata in index["files"]
            if file_metadata["language"].casefold() == language
        ]

    @staticmethod
    def _validate_index(index: dict):
        if (
            not isinstance(index, dict)
            or not isinstance(index.get("files"), list)
        ):
            raise RepositoryIndexError(
                "A valid repository index is required."
            )
