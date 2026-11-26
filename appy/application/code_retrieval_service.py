
from dataclasses import dataclass

from appy.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexResult,
)


class CodeRetrievalError(ValueError):
    """Raised when code retrieval fails."""


@dataclass(frozen=True)
class CodeRetrievalResult:
    """Contains retrieved code entities and retrieval metadata."""

    query_type: str
    query_value: str
    entries: tuple
    total_results: int


class CodeRetrievalService:
    """Retrieve code entities from a structured code index."""

    def get_by_id(
        self,
        index: CodeIndexResult,
        entity_id: str,
    ) -> CodeIndexEntry | None:
        """Retrieve one entity using its unique ID."""

        self._validate_index(index)
        self._validate_query(entity_id, "Entity ID")

        for entry in index.entries:
            if entry.entity_id == entity_id:
                return entry

        return None

    def get_by_qualified_name(
        self,
        index: CodeIndexResult,
        qualified_name: str,
    ) -> tuple:
        """Retrieve entities matching a qualified name."""

        self._validate_index(index)
        self._validate_query(qualified_name, "Qualified name")

        normalized = qualified_name.strip().casefold()

        return tuple(
            entry
            for entry in index.entries
            if entry.qualified_name.casefold() == normalized
        )

    def get_by_file(
        self,
        index: CodeIndexResult,
        filename: str,
    ) -> CodeRetrievalResult:
        """Retrieve all indexed entities belonging to a file."""

        self._validate_index(index)
        self._validate_query(filename, "Filename")

        normalized = filename.strip().replace("\\", "/").casefold()

        entries = tuple(
            entry
            for entry in index.entries
            if entry.filename.replace("\\", "/").casefold()
            == normalized
        )

        return self._create_result(
            "file",
            filename,
            entries,
        )

    def get_by_parent(
        self,
        index: CodeIndexResult,
        parent: str,
    ) -> CodeRetrievalResult:
        """Retrieve entities belonging to a parent class or module."""

        self._validate_index(index)
        self._validate_query(parent, "Parent")

        normalized = parent.strip().casefold()

        entries = tuple(
            entry
            for entry in index.entries
            if entry.parent is not None
            and entry.parent.casefold() == normalized
        )

        return self._create_result(
            "parent",
            parent,
            entries,
        )

    def get_by_line_range(
        self,
        index: CodeIndexResult,
        filename: str,
        start_line: int,
        end_line: int,
    ) -> CodeRetrievalResult:
        """Retrieve entities whose source ranges overlap the given range."""

        self._validate_index(index)
        self._validate_query(filename, "Filename")

        if (
            isinstance(start_line, bool)
            or not isinstance(start_line, int)
            or start_line < 1
        ):
            raise CodeRetrievalError(
                "Start line must be a positive integer."
            )

        if (
            isinstance(end_line, bool)
            or not isinstance(end_line, int)
            or end_line < start_line
        ):
            raise CodeRetrievalError(
                "End line must be greater than or equal to start line."
            )

        normalized = filename.strip().replace("\\", "/").casefold()

        entries = tuple(
            entry
            for entry in index.entries
            if (
                entry.filename.replace("\\", "/").casefold()
                == normalized
                and entry.line <= end_line
                and (entry.end_line or entry.line) >= start_line
            )
        )

        return self._create_result(
            "line_range",
            f"{filename}:{start_line}-{end_line}",
            entries,
        )

    @staticmethod
    def _validate_index(index):
        """Validate the supplied code index."""

        if not isinstance(index, CodeIndexResult):
            raise CodeRetrievalError(
                "Index must be a CodeIndexResult instance."
            )

        if not all(
            isinstance(entry, CodeIndexEntry)
            for entry in index.entries
        ):
            raise CodeRetrievalError(
                "Index contains invalid code entries."
            )

    @staticmethod
    def _validate_query(value, field_name):
        """Validate string-based retrieval parameters."""

        if not isinstance(value, str) or not value.strip():
            raise CodeRetrievalError(
                f"{field_name} must be a non-empty string."
            )

    @staticmethod
    def _create_result(
        query_type,
        query_value,
        entries,
    ):
        """Create a structured retrieval result."""

        return CodeRetrievalResult(
            query_type=query_type,
            query_value=query_value,
            entries=entries,
            total_results=len(entries),
        )
