
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from types import MappingProxyType
from typing import Any, Mapping


class MemoryModelError(ValueError):
    """Raised when an intelligence memory model is invalid."""


class MemoryType(str, Enum):
    """Supported categories of codebase knowledge."""

    REPOSITORY = "repository"
    FILE = "file"
    CODE_ENTITY = "code_entity"
    DEPENDENCY = "dependency"
    CALL_RELATIONSHIP = "call_relationship"
    INHERITANCE = "inheritance"
    CONFIGURATION = "configuration"
    ENTRY_POINT = "entry_point"
    ARCHITECTURE = "architecture"


@dataclass(frozen=True)
class IntelligenceMemory:
    """A structured piece of knowledge about a code repository."""

    memory_id: str
    repository_id: str
    memory_type: MemoryType
    content: str
    source_files: tuple[str, ...] = field(default_factory=tuple)
    related_entity_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        """Validate and normalize memory data."""

        self._validate_text(self.memory_id, "Memory ID")
        self._validate_text(self.repository_id, "Repository ID")
        self._validate_text(self.content, "Content")

        if not isinstance(self.memory_type, MemoryType):
            raise MemoryModelError(
                "Memory type must be a MemoryType value."
            )

        source_files = self._normalize_string_tuple(
            self.source_files,
            "Source files",
        )
        related_entity_ids = self._normalize_string_tuple(
            self.related_entity_ids,
            "Related entity IDs",
        )

        if not isinstance(self.metadata, Mapping):
            raise MemoryModelError("Metadata must be a mapping.")

        metadata = dict(self.metadata)

        try:
            json.dumps(metadata)
        except (TypeError, ValueError) as exc:
            raise MemoryModelError(
                "Metadata must contain JSON-serializable values."
            ) from exc

        self._validate_timestamp(self.created_at, "Created at")
        self._validate_timestamp(self.updated_at, "Updated at")

        object.__setattr__(self, "source_files", source_files)
        object.__setattr__(self, "related_entity_ids", related_entity_ids)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(metadata),
        )

    @staticmethod
    def _validate_text(value: str, field_name: str) -> None:
        """Ensure a required text field contains a non-empty string."""

        if not isinstance(value, str) or not value.strip():
            raise MemoryModelError(
                f"{field_name} must be a non-empty string."
            )

    @classmethod
    def _normalize_string_tuple(
        cls,
        values: tuple[str, ...],
        field_name: str,
    ) -> tuple[str, ...]:
        """Validate a collection of strings and convert it to a tuple."""

        if not isinstance(values, (list, tuple)):
            raise MemoryModelError(
                f"{field_name} must be a list or tuple."
            )

        normalized = []

        for value in values:
            cls._validate_text(value, field_name)
            normalized.append(value.strip())

        return tuple(normalized)

    @staticmethod
    def _validate_timestamp(value: str, field_name: str) -> None:
        """Require a valid timezone-aware ISO 8601 timestamp."""

        if not isinstance(value, str) or not value.strip():
            raise MemoryModelError(
                f"{field_name} must be a non-empty ISO timestamp."
            )

        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError as exc:
            raise MemoryModelError(
                f"{field_name} must be a valid ISO timestamp."
            ) from exc

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise MemoryModelError(
                f"{field_name} must include timezone information."
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert the memory record into JSON-compatible data."""

        return {
            "memory_id": self.memory_id,
            "repository_id": self.repository_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "source_files": list(self.source_files),
            "related_entity_ids": list(self.related_entity_ids),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntelligenceMemory":
        """Create a memory record from dictionary data."""

        if not isinstance(data, dict):
            raise MemoryModelError("Memory data must be a dictionary.")

        try:
            return cls(
                memory_id=data["memory_id"],
                repository_id=data["repository_id"],
                memory_type=MemoryType(data["memory_type"]),
                content=data["content"],
                source_files=data.get("source_files", ()),
                related_entity_ids=data.get("related_entity_ids", ()),
                metadata=data.get("metadata", {}),
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
        except KeyError as exc:
            raise MemoryModelError(
                f"Missing required memory field: {exc.args[0]}"
            ) from exc
        except ValueError as exc:
            if isinstance(exc, MemoryModelError):
                raise
            raise MemoryModelError(
                f"Invalid memory data: {exc}"
            ) from exc
