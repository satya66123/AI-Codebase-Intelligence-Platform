
from dataclasses import dataclass
from pathlib import Path

from appy.application.repository_input import (
    RepositoryInfo,
    validate_repository_path,
)
from appy.application.repository_scanner import (
    RepositoryScanner,
    RepositoryScanResult,
)
from appy.application.file_filtering_service import (
    FileFilteringService,
)
from appy.application.repository_map_service import (
    RepositoryMapService,
)
from appy.application.metadata_extraction_service import (
    MetadataExtractionService,
)
from appy.application.repository_index_service import (
    RepositoryIndexService,
)
from appy.application.repository_storage_service import (
    RepositoryStorageService,
)


@dataclass(frozen=True)
class RepositoryAnalysisResult:
    """Contains the completed repository discovery results."""

    repository: RepositoryInfo
    scan_result: RepositoryScanResult
    repository_map: str
    metadata: dict
    index: dict
    storage_path: Path | None


class RepositoryAgent:
    """Coordinates the repository discovery workflow."""

    def __init__(
        self,
        scanner=None,
        filtering_service=None,
        map_service=None,
        metadata_service=None,
        index_service=None,
        storage_service=None,
    ):
        self.scanner = scanner or RepositoryScanner()

        self.filtering_service = (
            filtering_service or FileFilteringService()
        )

        self.map_service = map_service or RepositoryMapService()

        self.metadata_service = (
            metadata_service or MetadataExtractionService()
        )

        self.index_service = (
            index_service or RepositoryIndexService()
        )

        self.storage_service = (
            storage_service or RepositoryStorageService()
        )

    def discover_repository(
        self,
        repository_path: str | Path,
        ignored_directories=None,
        ignored_files=None,
        respect_gitignore=True,
        save_index=True,
    ) -> RepositoryAnalysisResult:
        """Execute the complete repository discovery workflow."""

        # Step 1: Validate repository input.
        repository = validate_repository_path(repository_path)

        # Step 2: Discover repository files and directories.
        scan_result = self.scanner.scan(repository)

        # Step 3: Apply filtering and ignore rules.
        filtered_result = self.filtering_service.filter_files(
            scan_result=scan_result,
            ignored_directories=ignored_directories,
            ignored_files=ignored_files,
            respect_gitignore=respect_gitignore,
        )

        # Step 4: Generate repository directory map.
        repository_map = self.map_service.build_map(
            filtered_result
        )

        # Step 5: Extract repository metadata.
        metadata = self.metadata_service.extract_repository_metadata(
            filtered_result
        )

        # Step 6: Build searchable repository index.
        index = self.index_service.build_index(metadata)

        # Step 7: Persist the index when requested.
        storage_path = None

        if save_index:
            storage_path = self.storage_service.save_index(index)

        return RepositoryAnalysisResult(
            repository=repository,
            scan_result=filtered_result,
            repository_map=repository_map,
            metadata=metadata,
            index=index,
            storage_path=storage_path,
        )
