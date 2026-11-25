
from dataclasses import dataclass
from typing import Iterable

from app.application.code_entity_extractor import CodeEntity


class CodeIndexingError(ValueError):
    """Raised when code indexing fails."""


@dataclass(frozen=True)
class CodeIndexEntry:
    """Represents one searchable code entity in the index."""

    entity_id: str
    name: str
    entity_type: str
    qualified_name: str
    filename: str
    line: int
    end_line: int | None
    parent: str | None
    docstring: str | None
    normalized_name: str
    search_text: str


@dataclass(frozen=True)
class CodeIndexResult:
    """Contains the complete index and its statistics."""

    index_version: int
    entries: tuple
    total_entities: int
    total_files: int
    files: tuple
    entity_counts: dict
    by_file: dict


class CodeIndexingService:
    """Build a structured searchable index from extracted code entities."""

    INDEX_VERSION = 1

    def build_index(
        self,
        entities: Iterable[CodeEntity],
    ) -> CodeIndexResult:
        """Build an index from CodeEntity records."""

        if entities is None or isinstance(
            entities, (str, bytes, dict)
        ):
            raise CodeIndexingError(
                "Entities must be an iterable of CodeEntity objects."
            )

        try:
            entity_records = list(entities)
        except TypeError as exc:
            raise CodeIndexingError(
                "Entities must be iterable."
            ) from exc

        if not all(
            isinstance(entity, CodeEntity)
            for entity in entity_records
        ):
            raise CodeIndexingError(
                "Every item must be a CodeEntity instance."
            )

        entries = []
        entity_counts = {}
        by_file = {}

        for position, entity in enumerate(entity_records):
            self._validate_entity(entity)

            entry = self._create_entry(
                entity,
                position,
            )

            entries.append(entry)

            entity_counts[entry.entity_type] = (
                entity_counts.get(entry.entity_type, 0) + 1
            )

            by_file.setdefault(entry.filename, []).append(
                entry.entity_id
            )

        files = tuple(sorted(by_file))

        return CodeIndexResult(
            index_version=self.INDEX_VERSION,
            entries=tuple(entries),
            total_entities=len(entries),
            total_files=len(files),
            files=files,
            entity_counts=entity_counts,
            by_file={
                filename: tuple(entity_ids)
                for filename, entity_ids in by_file.items()
            },
        )

    @staticmethod
    def _validate_entity(entity: CodeEntity) -> None:
        """Validate required entity metadata."""

        required_fields = {
            "name": entity.name,
            "entity_type": entity.entity_type,
            "qualified_name": entity.qualified_name,
            "filename": entity.filename,
        }

        for field_name, value in required_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise CodeIndexingError(
                    f"Code entity {field_name} must be a non-empty string."
                )

        if not isinstance(entity.line, int) or entity.line < 1:
            raise CodeIndexingError(
                "Code entity line must be a positive integer."
            )

        if (
            entity.end_line is not None
            and (
                not isinstance(entity.end_line, int)
                or entity.end_line < entity.line
            )
        ):
            raise CodeIndexingError(
                "Code entity end_line must be greater than or equal to line."
            )

    @staticmethod
    def _create_entry(
        entity: CodeEntity,
        position: int,
    ) -> CodeIndexEntry:
        """Convert a CodeEntity into a searchable index entry."""

        normalized_name = entity.name.casefold()

        search_parts = [
            entity.name,
            entity.entity_type,
            entity.qualified_name,
            entity.filename,
        ]

        if entity.parent:
            search_parts.append(entity.parent)

        if entity.docstring:
            search_parts.append(entity.docstring)

        search_text = " ".join(search_parts).casefold()

        entity_id = (
            f"{entity.filename}::"
            f"{entity.qualified_name}::"
            f"{entity.line}::"
            f"{position}"
        )

        return CodeIndexEntry(
            entity_id=entity_id,
            name=entity.name,
            entity_type=entity.entity_type,
            qualified_name=entity.qualified_name,
            filename=entity.filename,
            line=entity.line,
            end_line=entity.end_line,
            parent=entity.parent,
            docstring=entity.docstring,
            normalized_name=normalized_name,
            search_text=search_text,
        )
