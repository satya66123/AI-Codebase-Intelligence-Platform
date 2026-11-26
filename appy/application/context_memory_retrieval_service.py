
import json
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from appy.application.intelligence_memory_models import (
    IntelligenceMemory,
    MemoryType,
)
from appy.application.intelligence_memory_storage import (
    IntelligenceMemoryStorage,
    IntelligenceMemoryStorageError,
)


class ContextMemoryRetrievalError(Exception):
    """Raised when context memory retrieval fails."""


@dataclass(frozen=True)
class ContextMemoryRetrievalResult:
    """Result returned by a context memory retrieval operation."""

    repository_id: str
    query: str
    memories: tuple[IntelligenceMemory, ...]
    total_matches: int

    def __post_init__(self) -> None:
        if not isinstance(self.repository_id, str) or not self.repository_id.strip():
            raise ContextMemoryRetrievalError(
                "Repository ID must be a non-empty string."
            )

        if not isinstance(self.query, str):
            raise ContextMemoryRetrievalError("Query must be a string.")

        if not isinstance(self.memories, tuple):
            raise ContextMemoryRetrievalError("Memories must be a tuple.")

        if any(
            not isinstance(memory, IntelligenceMemory)
            for memory in self.memories
        ):
            raise ContextMemoryRetrievalError(
                "Every retrieved item must be an IntelligenceMemory."
            )

        if (
            isinstance(self.total_matches, bool)
            or not isinstance(self.total_matches, int)
            or self.total_matches < 0
        ):
            raise ContextMemoryRetrievalError(
                "Total matches must be a non-negative integer."
            )

        if len(self.memories) > self.total_matches:
            raise ContextMemoryRetrievalError(
                "Retrieved memories cannot exceed total matches."
            )


class ContextMemoryRetrievalService:
    """Searches, filters, and ranks repository intelligence memories."""

    def __init__(self, storage: IntelligenceMemoryStorage) -> None:
        if not isinstance(storage, IntelligenceMemoryStorage):
            raise ContextMemoryRetrievalError(
                "A valid IntelligenceMemoryStorage instance is required."
            )

        self._storage = storage

    def retrieve(
        self,
        repository_id: str,
        query: str = "",
        memory_types: Optional[Iterable[MemoryType]] = None,
        source_file: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        limit: int = 10,
    ) -> ContextMemoryRetrievalResult:
        """Retrieve memories using optional filters and query ranking."""

        self._validate_repository_id(repository_id)
        self._validate_query(query)
        self._validate_optional_string(source_file, "Source file")
        self._validate_optional_string(
            related_entity_id, "Related entity ID"
        )
        self._validate_limit(limit)

        normalized_types = self._normalize_memory_types(memory_types)

        try:
            memories = self._storage.list_memories(repository_id)
        except IntelligenceMemoryStorageError as exc:
            raise ContextMemoryRetrievalError(
                f"Unable to load repository memories: {exc}"
            ) from exc

        filtered = [
            memory
            for memory in memories
            if self._matches_filters(
                memory,
                normalized_types,
                source_file,
                related_entity_id,
            )
        ]

        ranked = self._rank_memories(filtered, query)

        return ContextMemoryRetrievalResult(
            repository_id=repository_id,
            query=query,
            memories=tuple(ranked[:limit]),
            total_matches=len(ranked),
        )

    def retrieve_by_type(
        self,
        repository_id: str,
        memory_type: MemoryType,
        limit: int = 10,
    ) -> ContextMemoryRetrievalResult:
        """Retrieve memories belonging to a specific memory type."""

        if not isinstance(memory_type, MemoryType):
            raise ContextMemoryRetrievalError(
                "Memory type must be a valid MemoryType."
            )

        return self.retrieve(
            repository_id=repository_id,
            memory_types=(memory_type,),
            limit=limit,
        )

    def retrieve_by_source_file(
        self,
        repository_id: str,
        source_file: str,
        limit: int = 10,
    ) -> ContextMemoryRetrievalResult:
        """Retrieve memories associated with a source file."""

        return self.retrieve(
            repository_id=repository_id,
            source_file=source_file,
            limit=limit,
        )

    def retrieve_by_entity(
        self,
        repository_id: str,
        related_entity_id: str,
        limit: int = 10,
    ) -> ContextMemoryRetrievalResult:
        """Retrieve memories associated with a code entity."""

        return self.retrieve(
            repository_id=repository_id,
            related_entity_id=related_entity_id,
            limit=limit,
        )

    @staticmethod
    def _matches_filters(
        memory: IntelligenceMemory,
        memory_types: Optional[tuple[MemoryType, ...]],
        source_file: Optional[str],
        related_entity_id: Optional[str],
    ) -> bool:
        if memory_types is not None and memory.memory_type not in memory_types:
            return False

        if source_file is not None and source_file not in memory.source_files:
            return False

        if (
            related_entity_id is not None
            and related_entity_id not in memory.related_entity_ids
        ):
            return False

        return True

    @classmethod
    def _rank_memories(
        cls,
        memories: list[IntelligenceMemory],
        query: str,
    ) -> list[IntelligenceMemory]:
        if not query.strip():
            return sorted(
                memories,
                key=lambda memory: (
                    memory.updated_at,
                    memory.memory_id,
                ),
                reverse=True,
            )

        query_tokens = set(cls._tokenize(query))
        normalized_query = query.casefold().strip()
        scored = []

        for memory in memories:
            searchable_text = cls._memory_search_text(memory)
            normalized_text = searchable_text.casefold()
            memory_tokens = set(cls._tokenize(searchable_text))

            score = len(query_tokens.intersection(memory_tokens))

            if normalized_query in normalized_text:
                score += 3

            if score > 0:
                scored.append((score, memory))

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].updated_at,
                item[1].memory_id,
            ),
            reverse=True,
        )

        return [memory for _, memory in scored]

    @staticmethod
    def _memory_search_text(memory: IntelligenceMemory) -> str:
        content = json.dumps(memory.content, sort_keys=True, default=str)
        metadata = json.dumps(
            dict(memory.metadata),
            sort_keys=True,
            default=str,
        )

        return " ".join(
            (
                memory.memory_id,
                memory.repository_id,
                memory.memory_type.value,
                content,
                metadata,
                " ".join(memory.source_files),
                " ".join(memory.related_entity_ids),
            )
        )

    @staticmethod
    def _tokenize(value: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9_]+", value.casefold())

    @staticmethod
    def _validate_repository_id(repository_id: str) -> None:
        if not isinstance(repository_id, str) or not repository_id.strip():
            raise ContextMemoryRetrievalError(
                "Repository ID must be a non-empty string."
            )

    @staticmethod
    def _validate_query(query: str) -> None:
        if not isinstance(query, str):
            raise ContextMemoryRetrievalError("Query must be a string.")

    @staticmethod
    def _validate_optional_string(
        value: Optional[str],
        label: str,
    ) -> None:
        if value is not None and (
            not isinstance(value, str) or not value.strip()
        ):
            raise ContextMemoryRetrievalError(
                f"{label} must be a non-empty string when provided."
            )

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ContextMemoryRetrievalError(
                "Limit must be a positive integer."
            )

    @staticmethod
    def _normalize_memory_types(
        memory_types: Optional[Iterable[MemoryType]],
    ) -> Optional[tuple[MemoryType, ...]]:
        if memory_types is None:
            return None

        if isinstance(memory_types, (str, bytes)):
            raise ContextMemoryRetrievalError(
                "Memory types must be an iterable of MemoryType values."
            )

        try:
            normalized = tuple(memory_types)
        except TypeError as exc:
            raise ContextMemoryRetrievalError(
                "Memory types must be iterable."
            ) from exc

        if any(not isinstance(item, MemoryType) for item in normalized):
            raise ContextMemoryRetrievalError(
                "Every memory type must be a valid MemoryType."
            )

        return normalized
