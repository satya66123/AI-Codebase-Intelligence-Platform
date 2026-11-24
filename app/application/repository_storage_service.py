
import json
import os
import tempfile
from pathlib import Path


class RepositoryStorageError(RuntimeError):
    """Raised when repository index storage fails."""


class RepositoryStorageService:
    """Stores and retrieves repository indexes using JSON."""

    def __init__(self, storage_directory="data/repositories"):
        self.storage_directory = Path(storage_directory)

    def _get_storage_path(self, repository_name: str) -> Path:
        if (
            not isinstance(repository_name, str)
            or not repository_name.strip()
            or repository_name in {".", ".."}
            or Path(repository_name).name != repository_name
            or "/" in repository_name
            or "\\" in repository_name
        ):
            raise RepositoryStorageError(
                "Invalid repository name."
            )

        return self.storage_directory / f"{repository_name}.json"

    def save_index(self, index: dict) -> Path:
        """Save a repository index as a JSON file."""

        if not isinstance(index, dict):
            raise RepositoryStorageError(
                "Repository index must be a dictionary."
            )

        repository_name = index.get("repository_name")

        storage_path = self._get_storage_path(repository_name)

        try:
            self.storage_directory.mkdir(
                parents=True,
                exist_ok=True
            )

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".tmp",
                dir=self.storage_directory,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

                json.dump(
                    index,
                    temporary_file,
                    indent=4,
                    ensure_ascii=False,
                )

            os.replace(temporary_path, storage_path)

            return storage_path

        except (OSError, TypeError, ValueError) as exc:
            if "temporary_path" in locals():
                temporary_path.unlink(missing_ok=True)

            raise RepositoryStorageError(
                "Unable to save repository index."
            ) from exc

    def load_index(self, repository_name: str) -> dict:
        """Load a previously saved repository index."""

        storage_path = self._get_storage_path(repository_name)

        if not storage_path.is_file():
            raise RepositoryStorageError(
                "Repository index does not exist."
            )

        try:
            with storage_path.open(
                "r",
                encoding="utf-8"
            ) as file:
                index = json.load(file)

        except (OSError, json.JSONDecodeError) as exc:
            raise RepositoryStorageError(
                "Unable to load repository index."
            ) from exc

        if not isinstance(index, dict):
            raise RepositoryStorageError(
                "Stored repository index is invalid."
            )

        return index

    def delete_index(self, repository_name: str) -> bool:
        """Delete a stored repository index."""

        storage_path = self._get_storage_path(repository_name)

        if not storage_path.is_file():
            return False

        try:
            storage_path.unlink()
            return True

        except OSError as exc:
            raise RepositoryStorageError(
                "Unable to delete repository index."
            ) from exc

    def list_indexes(self) -> list:
        """List all stored repository index names."""

        if not self.storage_directory.exists():
            return []

        try:
            return sorted(
                path.stem
                for path in self.storage_directory.glob("*.json")
                if path.is_file()
            )

        except OSError as exc:
            raise RepositoryStorageError(
                "Unable to list repository indexes."
            ) from exc
