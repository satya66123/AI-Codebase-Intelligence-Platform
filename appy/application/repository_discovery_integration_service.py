
from pathlib import Path

from appy.application.repository_agent import (
    RepositoryAgent,
    RepositoryAnalysisResult,
)
from appy.application.repository_index_service import (
    RepositoryIndexService,
)


class RepositoryDiscoveryIntegrationError(RuntimeError):
    """Raised when repository integration operations fail."""


class RepositoryDiscoveryIntegrationService:
    """Provides a unified interface to repository discovery."""

    def __init__(
        self,
        repository_agent=None,
        index_service=None,
    ):
        self.repository_agent = (
            repository_agent or RepositoryAgent()
        )

        self.index_service = (
            index_service or RepositoryIndexService()
        )

        self._last_result = None

    def discover(
        self,
        repository_path: str | Path,
        ignored_directories=None,
        ignored_files=None,
        respect_gitignore=True,
        save_index=True,
    ) -> RepositoryAnalysisResult:
        """Discover and analyze a repository."""

        try:
            result = self.repository_agent.discover_repository(
                repository_path=repository_path,
                ignored_directories=ignored_directories,
                ignored_files=ignored_files,
                respect_gitignore=respect_gitignore,
                save_index=save_index,
            )

            self._last_result = result
            return result

        except Exception as exc:
            raise RepositoryDiscoveryIntegrationError(
                "Repository discovery integration failed."
            ) from exc

    def get_repository_map(self) -> str:
        """Return the latest repository directory map."""

        result = self._require_result()
        return result.repository_map

    def get_repository_metadata(self) -> dict:
        """Return metadata from the latest discovery."""

        result = self._require_result()
        return result.metadata

    def get_repository_index(self) -> dict:
        """Return the latest searchable repository index."""

        result = self._require_result()
        return result.index

    def search_files(self, query: str) -> list:
        """Search files in the latest repository index."""

        result = self._require_result()

        return self.index_service.search_files(
            result.index,
            query,
        )

    def get_file_metadata(self, relative_path: str):
        """Retrieve file metadata by repository-relative path."""

        result = self._require_result()

        return self.index_service.get_file(
            result.index,
            relative_path,
        )

    def load_saved_index(self, repository_name: str) -> dict:
        """Load a previously persisted repository index."""

        try:
            return self.repository_agent.storage_service.load_index(
                repository_name
            )
        except Exception as exc:
            raise RepositoryDiscoveryIntegrationError(
                "Unable to load saved repository index."
            ) from exc

    def _require_result(self) -> RepositoryAnalysisResult:
        if self._last_result is None:
            raise RepositoryDiscoveryIntegrationError(
                "Discover a repository before requesting its results."
            )

        return self._last_result


    def restore_result(
        self,
        result: RepositoryAnalysisResult,
    ) -> None:
        """Restore a previously discovered repository result."""

        if result is None:
            raise RepositoryDiscoveryIntegrationError(
                "A valid repository result is required."
            )

        self._last_result = result

