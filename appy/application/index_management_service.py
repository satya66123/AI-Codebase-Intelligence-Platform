
from dataclasses import dataclass
from datetime import datetime, timezone

from appy.application.code_indexing_service import CodeIndexResult


class IndexManagementError(ValueError):
    """Raised when index management fails."""


@dataclass(frozen=True)
class ManagedIndex:
    """Represents a registered code index."""

    index_id: str
    index: CodeIndexResult
    version: int
    created_at: str
    updated_at: str
    total_entities: int
    total_files: int


class IndexManagementService:
    """Manage registered code indexes."""

    def __init__(self):
        self._indexes = {}

    def register_index(
        self,
        index_id: str,
        index: CodeIndexResult,
    ) -> ManagedIndex:
        """Register a new code index."""

        self._validate_index_id(index_id)
        self._validate_index(index)

        if index_id in self._indexes:
            raise IndexManagementError(
                f"Index already exists: {index_id}"
            )

        timestamp = self._current_timestamp()

        managed_index = ManagedIndex(
            index_id=index_id,
            index=index,
            version=1,
            created_at=timestamp,
            updated_at=timestamp,
            total_entities=index.total_entities,
            total_files=index.total_files,
        )

        self._indexes[index_id] = managed_index

        return managed_index

    def get_index(self, index_id: str) -> ManagedIndex | None:
        """Retrieve a registered index."""

        self._validate_index_id(index_id)

        return self._indexes.get(index_id)

    def update_index(
        self,
        index_id: str,
        index: CodeIndexResult,
    ) -> ManagedIndex:
        """Replace an existing index and increment its version."""

        self._validate_index_id(index_id)
        self._validate_index(index)

        existing = self._indexes.get(index_id)

        if existing is None:
            raise IndexManagementError(
                f"Index does not exist: {index_id}"
            )

        managed_index = ManagedIndex(
            index_id=index_id,
            index=index,
            version=existing.version + 1,
            created_at=existing.created_at,
            updated_at=self._current_timestamp(),
            total_entities=index.total_entities,
            total_files=index.total_files,
        )

        self._indexes[index_id] = managed_index

        return managed_index

    def delete_index(self, index_id: str) -> bool:
        """Delete a registered index."""

        self._validate_index_id(index_id)

        return self._indexes.pop(index_id, None) is not None

    def list_indexes(self) -> tuple:
        """Return all registered indexes."""

        return tuple(self._indexes.values())

    def get_index_count(self) -> int:
        """Return the number of registered indexes."""

        return len(self._indexes)

    @staticmethod
    def _validate_index_id(index_id: str) -> None:
        """Validate an index identifier."""

        if not isinstance(index_id, str) or not index_id.strip():
            raise IndexManagementError(
                "Index ID must be a non-empty string."
            )

    @staticmethod
    def _validate_index(index: CodeIndexResult) -> None:
        """Validate an index object."""

        if not isinstance(index, CodeIndexResult):
            raise IndexManagementError(
                "Index must be a CodeIndexResult instance."
            )

    @staticmethod
    def _current_timestamp() -> str:
        """Return a timezone-aware UTC timestamp."""

        return datetime.now(timezone.utc).isoformat()
