
"""Manage the lifecycle of repository intelligence memories."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from appy.application.intelligence_memory_models import (
    IntelligenceMemory,
    MemoryType,
)
from appy.application.intelligence_memory_storage import (
    IntelligenceMemoryStorage,
    IntelligenceMemoryStorageError,
)


class IntelligenceMemoryManagementError(Exception):
    """Raised when a memory management operation fails."""


class MemoryAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    DELETED_BY_TYPE = "deleted_by_type"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class MemoryManagementResult:
    """Result of a memory management operation."""

    repository_id: str
    action: MemoryAction
    affected_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.repository_id, str) or not self.repository_id.strip():
            raise ValueError("repository_id must be a non-empty string.")

        if not isinstance(self.action, MemoryAction):
            raise ValueError("action must be a MemoryAction.")

        if (
            not isinstance(self.affected_count, int)
            or isinstance(self.affected_count, bool)
            or self.affected_count < 0
        ):
            raise ValueError("affected_count must be a non-negative integer.")


@dataclass(frozen=True)
class RepositoryMemorySummary:
    """Summary of stored memories for one repository."""

    repository_id: str
    total_memories: int
    memories_by_type: Dict[str, int]


class IntelligenceMemoryManagementService:
    """Coordinate creation, updates, deletion and summaries of memories."""

    def __init__(self, storage: IntelligenceMemoryStorage) -> None:
        if not isinstance(storage, IntelligenceMemoryStorage):
            raise IntelligenceMemoryManagementError(
                "storage must be an IntelligenceMemoryStorage instance."
            )

        self._storage = storage

    @staticmethod
    def _validate_repository_id(repository_id: str) -> None:
        if not isinstance(repository_id, str) or not repository_id.strip():
            raise IntelligenceMemoryManagementError(
                "repository_id must be a non-empty string."
            )

    @staticmethod
    def _validate_memory(memory: IntelligenceMemory) -> None:
        if not isinstance(memory, IntelligenceMemory):
            raise IntelligenceMemoryManagementError(
                "memory must be an IntelligenceMemory instance."
            )

    @staticmethod
    def _validate_memory_type(memory_type: MemoryType) -> None:
        if not isinstance(memory_type, MemoryType):
            raise IntelligenceMemoryManagementError(
                "memory_type must be a MemoryType value."
            )

    def save_memory(
        self, memory: IntelligenceMemory
    ) -> MemoryManagementResult:
        """Save a new memory. Existing IDs are not overwritten."""

        self._validate_memory(memory)

        try:
            self._storage.save(memory)
        except IntelligenceMemoryStorageError as exc:
            raise IntelligenceMemoryManagementError(
                f"Could not save memory '{memory.memory_id}'."
            ) from exc

        return MemoryManagementResult(
            repository_id=memory.repository_id,
            action=MemoryAction.CREATED,
            affected_count=1,
        )

    def update_memory(
        self, memory: IntelligenceMemory
    ) -> MemoryManagementResult:
        """Update an existing memory without changing its creation history."""

        self._validate_memory(memory)

        try:
            existing = self._storage.load(
                memory.repository_id,
                memory.memory_id,
            )

            if existing is None:
                raise IntelligenceMemoryManagementError(
                    f"Memory '{memory.memory_id}' does not exist."
                )

            updated_memory = IntelligenceMemory(
                memory_id=memory.memory_id,
                repository_id=memory.repository_id,
                memory_type=memory.memory_type,
                content=memory.content,
                source_files=memory.source_files,
                related_entity_ids=memory.related_entity_ids,
                metadata=memory.metadata,
                created_at=existing.created_at,
                updated_at=memory.updated_at,
            )

            self._storage.update(updated_memory)

        except IntelligenceMemoryManagementError:
            raise
        except IntelligenceMemoryStorageError as exc:
            raise IntelligenceMemoryManagementError(
                f"Could not update memory '{memory.memory_id}'."
            ) from exc

        return MemoryManagementResult(
            repository_id=memory.repository_id,
            action=MemoryAction.UPDATED,
            affected_count=1,
        )

    def upsert_memory(
        self, memory: IntelligenceMemory
    ) -> MemoryManagementResult:
        """Create a memory if missing; otherwise update it."""

        self._validate_memory(memory)

        try:
            existing = self._storage.load(
                memory.repository_id,
                memory.memory_id,
            )
        except IntelligenceMemoryStorageError as exc:
            raise IntelligenceMemoryManagementError(
                f"Could not inspect memory '{memory.memory_id}'."
            ) from exc

        if existing is None:
            return self.save_memory(memory)

        return self.update_memory(memory)

    def delete_memory(
        self,
        repository_id: str,
        memory_id: str,
    ) -> MemoryManagementResult:
        """Delete one memory."""

        self._validate_repository_id(repository_id)

        if not isinstance(memory_id, str) or not memory_id.strip():
            raise IntelligenceMemoryManagementError(
                "memory_id must be a non-empty string."
            )

        try:
            deleted = self._storage.delete(repository_id, memory_id)
        except IntelligenceMemoryStorageError as exc:
            raise IntelligenceMemoryManagementError(
                f"Could not delete memory '{memory_id}'."
            ) from exc

        return MemoryManagementResult(
            repository_id=repository_id,
            action=MemoryAction.DELETED,
            affected_count=1 if deleted else 0,
        )

    def delete_memories_by_type(
        self,
        repository_id: str,
        memory_type: MemoryType,
    ) -> MemoryManagementResult:
        """Delete all memories of a selected type in a repository."""

        self._validate_repository_id(repository_id)
        self._validate_memory_type(memory_type)

        try:
            memories = self._storage.list_memories(repository_id)

            matching_memories = [
                memory
                for memory in memories
                if memory.memory_type == memory_type
            ]

            deleted_count = 0

            for memory in matching_memories:
                if self._storage.delete(repository_id, memory.memory_id):
                    deleted_count += 1

        except IntelligenceMemoryStorageError as exc:
            raise IntelligenceMemoryManagementError(
                "Could not delete memories by type."
            ) from exc

        return MemoryManagementResult(
            repository_id=repository_id,
            action=MemoryAction.DELETED_BY_TYPE,
            affected_count=deleted_count,
        )

    def get_repository_summary(
        self,
        repository_id: str,
    ) -> RepositoryMemorySummary:
        """Return the total and per-type memory counts."""

        self._validate_repository_id(repository_id)

        try:
            memories = self._storage.list_memories(repository_id)
        except IntelligenceMemoryStorageError as exc:
            raise IntelligenceMemoryManagementError(
                "Could not retrieve repository memory summary."
            ) from exc

        counts = {memory_type.value: 0 for memory_type in MemoryType}

        for memory in memories:
            counts[memory.memory_type.value] += 1

        return RepositoryMemorySummary(
            repository_id=repository_id,
            total_memories=len(memories),
            memories_by_type=counts,
        )
