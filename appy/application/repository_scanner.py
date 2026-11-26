
from dataclasses import dataclass
from pathlib import Path
import os

from appy.application.repository_input import RepositoryInfo

class RepositoryScanError(RuntimeError):
    """Raised when repository scanning fails."""

    def __init__(self, message: str, code: str = "SCAN_FAILED"):
        super().__init__(message)
        self.code = code

@dataclass(frozen=True)
class RepositoryScanResult:
    root: Path
    files: tuple[Path, ...]
    directories: tuple[Path, ...]
    symlinks: tuple[Path, ...]

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_directories(self) -> int:
        return len(self.directories)

    @property
    def total_symlinks(self) -> int:
        return len(self.symlinks)

class RepositoryScanner:
    """Recursively discovers entries in a local repository."""

    def scan(self, repository: RepositoryInfo) -> RepositoryScanResult:
        if not isinstance(repository, RepositoryInfo):
            raise RepositoryScanError(
                "A valid RepositoryInfo object is required.",
                "INVALID_REPOSITORY"
            )

        root = repository.root

        if not root.exists() or not root.is_dir():
            raise RepositoryScanError(
                "Repository directory is unavailable.",
                "INVALID_REPOSITORY_PATH"
            )

        files = []
        directories = []
        symlinks = []

        pending_directories = [root]

        try:
            while pending_directories:
                current_directory = pending_directories.pop()

                with os.scandir(current_directory) as entries:
                    sorted_entries = sorted(
                        entries,
                        key=lambda entry: entry.name.lower()
                    )

                child_directories = []

                for entry in sorted_entries:
                    entry_path = Path(entry.path)

                    if entry.is_symlink():
                        symlinks.append(entry_path)

                    elif entry.is_dir(follow_symlinks=False):
                        directories.append(entry_path)
                        child_directories.append(entry_path)

                    elif entry.is_file(follow_symlinks=False):
                        files.append(entry_path)

                # Reverse insertion preserves alphabetical DFS order.
                pending_directories.extend(
                    reversed(child_directories)
                )

        except OSError as exc:
            raise RepositoryScanError(
                f"Unable to scan repository: {exc}",
                "DIRECTORY_SCAN_FAILED"
            ) from exc

        return RepositoryScanResult(
            root=root,
            files=tuple(files),
            directories=tuple(directories),
            symlinks=tuple(symlinks)
        )