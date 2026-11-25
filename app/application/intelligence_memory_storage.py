
import hashlib
import json
from pathlib import Path
from typing import Any

from app.application.intelligence_memory_models import (
    IntelligenceMemory,
    MemoryModelError,
)


class IntelligenceMemoryStorageError(ValueError):
    """Raised when intelligence memory storage operations fail."""


class IntelligenceMemoryStorage:
    """Persist intelligence memories as individual JSON files."""

    def __init__(self, storage_dir: str | Path = "data/intelligence_memory"):
        if not isinstance(storage_dir, (str, Path)):
            raise IntelligenceMemoryStorageError(
                "Storage directory must be a path."
            )

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, memory: IntelligenceMemory) -> IntelligenceMemory:
        """Save a new memory. Existing memory IDs are rejected."""

        self._validate_memory(memory)

        path = self._memory_path(
            memory.repository_id,
            memory.memory_id,
        )

        if path.exists():
            raise IntelligenceMemoryStorageError(
                f"Memory already exists: {memory.memory_id}"
            )

        self._write_memory(path, memory)
        return memory

    def load(
        self,
        repository_id: str,
        memory_id: str,
    ) -> IntelligenceMemory | None:
        """Load a memory by repository ID and memory ID."""

        self._validate_identifier(repository_id, "Repository ID")
        self._validate_identifier(memory_id, "Memory ID")

        path = self._memory_path(repository_id, memory_id)

        if not path.exists():
            return None

        return self._read_memory(path)

    def update(self, memory: IntelligenceMemory) -> IntelligenceMemory:
        """Replace an existing memory while preserving its creation time."""

        self._validate_memory(memory)

        path = self._memory_path(
            memory.repository_id,
            memory.memory_id,
        )

        if not path.exists():
            raise IntelligenceMemoryStorageError(
                f"Memory does not exist: {memory.memory_id}"
            )

        existing = self._read_memory(path)

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

        self._write_memory(path, updated_memory)
        return updated_memory

    def delete(self, repository_id: str, memory_id: str) -> bool:
        """Delete a memory. Return False if it does not exist."""

        self._validate_identifier(repository_id, "Repository ID")
        self._validate_identifier(memory_id, "Memory ID")

        path = self._memory_path(repository_id, memory_id)

        if not path.exists():
            return False

        path.unlink()
        return True

    def list_memories(
        self,
        repository_id: str,
    ) -> tuple[IntelligenceMemory, ...]:
        """Return all memories belonging to a repository."""

        self._validate_identifier(repository_id, "Repository ID")

        repository_dir = self._repository_path(repository_id)

        if not repository_dir.exists():
            return ()

        memories = []

        for path in sorted(repository_dir.glob("*.json")):
            memory = self._read_memory(path)

            if memory.repository_id != repository_id:
                raise IntelligenceMemoryStorageError(
                    f"Repository mismatch in stored memory: {path.name}"
                )

            memories.append(memory)

        return tuple(memories)

    def count_memories(self, repository_id: str) -> int:
        """Return the number of stored memories for a repository."""

        return len(self.list_memories(repository_id))

    def _write_memory(
        self,
        path: Path,
        memory: IntelligenceMemory,
    ) -> None:
        """Write JSON using a temporary file and atomic replacement."""

        temporary_path = path.with_suffix(".tmp")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(
                    memory.to_dict(),
                    file,
                    indent=4,
                    ensure_ascii=False,
                )

            temporary_path.replace(path)

        except (OSError, TypeError, ValueError) as exc:
            temporary_path.unlink(missing_ok=True)
            raise IntelligenceMemoryStorageError(
                f"Could not write memory: {memory.memory_id}"
            ) from exc

    @staticmethod
    def _read_memory(path: Path) -> IntelligenceMemory:
        """Read and validate one stored memory JSON file."""

        try:
            with path.open("r", encoding="utf-8") as file:
                data: Any = json.load(file)

            return IntelligenceMemory.from_dict(data)

        except (OSError, json.JSONDecodeError, MemoryModelError) as exc:
            raise IntelligenceMemoryStorageError(
                f"Could not read stored memory: {path.name}"
            ) from exc

    def _memory_path(
        self,
        repository_id: str,
        memory_id: str,
    ) -> Path:
        """Build a safe path for a memory record."""

        repository_dir = self._repository_path(repository_id)
        memory_filename = self._hash_identifier(memory_id) + ".json"

        return repository_dir / memory_filename

    def _repository_path(self, repository_id: str) -> Path:
        """Build a safe directory path for a repository."""

        repository_folder = self._hash_identifier(repository_id)
        return self.storage_dir / repository_folder

    @staticmethod
    def _hash_identifier(value: str) -> str:
        """Create a filesystem-safe identifier."""

        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_identifier(value: str, field_name: str) -> None:
        """Validate a repository or memory identifier."""

        if not isinstance(value, str) or not value.strip():
            raise IntelligenceMemoryStorageError(
                f"{field_name} must be a non-empty string."
            )

    @staticmethod
    def _validate_memory(memory: IntelligenceMemory) -> None:
        """Validate the memory object before persistence."""

        if not isinstance(memory, IntelligenceMemory):
            raise IntelligenceMemoryStorageError(
                "Memory must be an IntelligenceMemory instance."
            )
