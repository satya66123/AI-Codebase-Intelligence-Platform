
from dataclasses import dataclass
from pathlib import Path
import os

class RepositoryInputError(ValueError):
    """Raised when repository input is invalid."""

    def __init__(self, message: str, code: str = "INVALID_REPOSITORY"):
        super().__init__(message)
        self.code = code

@dataclass(frozen=True)
class RepositoryInfo:
    root: Path
    name: str
    is_git_repository: bool

def validate_repository_path(value: str | os.PathLike) -> RepositoryInfo:
    """
    Validate a local repository path and return repository information.
    """

    if value is None:
        raise RepositoryInputError(
            "Repository path cannot be None.",
            "EMPTY_PATH"
        )

    if not isinstance(value, (str, os.PathLike)):
        raise RepositoryInputError(
            "Repository path must be a string or path-like value.",
            "INVALID_PATH_TYPE"
        )

    raw_path = os.fspath(value)

    if not raw_path.strip():
        raise RepositoryInputError(
            "Repository path cannot be empty.",
            "EMPTY_PATH"
        )

    try:
        repository_path = Path(raw_path).expanduser().resolve(strict=True)

    except (OSError, RuntimeError) as exc:
        raise RepositoryInputError(
            "Unable to resolve repository path.",
            "PATH_RESOLUTION_FAILED"
        ) from exc

    if not repository_path.exists():
        raise RepositoryInputError(
            "Repository does not exist.",
            "PATH_NOT_FOUND"
        )

    if not repository_path.is_dir():
        raise RepositoryInputError(
            "Provided path is not a directory.",
            "NOT_A_DIRECTORY"
        )

    if not os.access(repository_path, os.R_OK | os.X_OK):
        raise RepositoryInputError(
            "Repository directory is not accessible.",
            "ACCESS_DENIED"
        )

    try:
        entries = list(repository_path.iterdir())
    except OSError as exc:
        raise RepositoryInputError(
            "Unable to read repository directory.",
            "DIRECTORY_READ_FAILED"
        ) from exc

    if not entries or all(entry.name == ".git" for entry in entries):
        raise RepositoryInputError(
            "Repository directory is empty.",
            "EMPTY_REPOSITORY"
        )

    git_path = repository_path / ".git"

    return RepositoryInfo(
        root=repository_path,
        name=repository_path.name,
        is_git_repository=git_path.is_dir() or git_path.is_file()
    )