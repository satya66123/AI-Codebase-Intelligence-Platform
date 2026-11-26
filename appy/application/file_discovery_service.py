
from appy.application.repository_input import RepositoryInfo
from appy.application.repository_scanner import (
    RepositoryScanner,
    RepositoryScanError,
    RepositoryScanResult,
)


class FileDiscoveryService:
    """Provides repository file discovery and statistics."""

    def __init__(self, scanner=None):
        self.scanner = scanner or RepositoryScanner()

    def discover(
        self,
        repository: RepositoryInfo
    ) -> RepositoryScanResult:
        """
        Discover files and directories in the supplied repository.

        Returns the scanner's complete discovery result.
        """
        if not isinstance(repository, RepositoryInfo):
            raise RepositoryScanError(
                "A valid RepositoryInfo object is required.",
                "INVALID_REPOSITORY"
            )

        return self.scanner.scan(repository)

    @staticmethod
    def get_statistics(
        result: RepositoryScanResult
    ) -> dict:
        """Return basic statistics from a discovery result."""

        if not isinstance(result, RepositoryScanResult):
            raise ValueError(
                "A valid RepositoryScanResult object is required."
            )

        return {
            "repository_name": result.root.name,
            "total_files": result.total_files,
            "total_directories": result.total_directories,
            "total_symlinks": result.total_symlinks,
        }
