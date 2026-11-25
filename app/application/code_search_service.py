
from app.application.code_indexing_service import (
    CodeIndexResult,
    CodeIndexEntry,
)


class CodeSearchError(ValueError):
    """Raised when code search fails."""


class CodeSearchService:
    """Search code entities in a structured code index."""

    def search(
        self,
        index: CodeIndexResult,
        query: str,
        entity_type: str | None = None,
        exact_match: bool = False,
    ) -> tuple:
        """Search indexed code entities."""

        if not isinstance(index, CodeIndexResult):
            raise CodeSearchError(
                "Index must be a CodeIndexResult instance."
            )

        if not isinstance(query, str) or not query.strip():
            raise CodeSearchError(
                "Search query must be a non-empty string."
            )

        if entity_type is not None:
            if not isinstance(entity_type, str) or not entity_type.strip():
                raise CodeSearchError(
                    "Entity type must be a non-empty string."
                )

            entity_type = entity_type.strip().casefold()

        if not isinstance(exact_match, bool):
            raise CodeSearchError(
                "exact_match must be a boolean."
            )

        normalized_query = query.strip().casefold()

        results = []

        for entry in index.entries:
            if not isinstance(entry, CodeIndexEntry):
                raise CodeSearchError(
                    "Index contains an invalid entry."
                )

            if entity_type and entry.entity_type.casefold() != entity_type:
                continue

            if self._matches(
                entry,
                normalized_query,
                exact_match,
            ):
                results.append(entry)

        return tuple(results)

    @staticmethod
    def _matches(
        entry: CodeIndexEntry,
        query: str,
        exact_match: bool,
    ) -> bool:
        """Determine whether an index entry matches the query."""

        if exact_match:
            searchable_fields = (
                entry.name,
                entry.qualified_name,
                entry.filename,
            )

            return any(
                field.casefold() == query
                for field in searchable_fields
            )

        return query in entry.search_text
