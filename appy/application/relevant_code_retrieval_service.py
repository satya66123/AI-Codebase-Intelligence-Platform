
from dataclasses import dataclass

from appy.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexResult,
)
from appy.application.relevant_file_retrieval_service import (
    RelevantFileRetrievalResult,
)


class RelevantCodeRetrievalError(ValueError):
    """Raised when relevant code retrieval fails."""


@dataclass(frozen=True)
class RelevantCodeRetrievalResult:
    """Contains code entities retrieved from relevant files."""

    question: str
    total_code_entities: int
    code_entities: tuple

    def __post_init__(self):
        if not isinstance(self.question, str) or not self.question.strip():
            raise RelevantCodeRetrievalError(
                "Question must be a non-empty string."
            )

        if (
            not isinstance(self.total_code_entities, int)
            or isinstance(self.total_code_entities, bool)
            or self.total_code_entities < 0
        ):
            raise RelevantCodeRetrievalError(
                "Total code entities must be a non-negative integer."
            )

        if not isinstance(self.code_entities, tuple):
            raise RelevantCodeRetrievalError(
                "Code entities must be a tuple."
            )

        if self.total_code_entities != len(self.code_entities):
            raise RelevantCodeRetrievalError(
                "Total code entities must match the number of entities."
            )

        if not all(
            isinstance(entity, CodeIndexEntry)
            for entity in self.code_entities
        ):
            raise RelevantCodeRetrievalError(
                "Every code entity must be a CodeIndexEntry instance."
            )


class RelevantCodeRetrievalService:
    """Retrieve indexed code entities from relevant repository files."""

    def retrieve(
        self,
        index: CodeIndexResult,
        relevant_files: RelevantFileRetrievalResult,
        limit: int = 50,
    ) -> RelevantCodeRetrievalResult:
        """Retrieve code entities belonging to relevant files."""

        self._validate_index(index)
        self._validate_relevant_files(relevant_files)
        self._validate_limit(limit)

        try:
            relevant_filenames = {
                file_result.filename
                for file_result in relevant_files.files
            }

            entities = [
                entry
                for entry in index.entries
                if entry.filename in relevant_filenames
            ]

            entities.sort(
                key=lambda entry: (
                    entry.filename,
                    entry.line,
                    entry.qualified_name,
                    entry.entity_id,
                )
            )

            selected_entities = tuple(entities[:limit])

            return RelevantCodeRetrievalResult(
                question=relevant_files.question,
                total_code_entities=len(selected_entities),
                code_entities=selected_entities,
            )

        except RelevantCodeRetrievalError:
            raise
        except Exception as exc:
            raise RelevantCodeRetrievalError(
                "Unable to retrieve relevant code entities."
            ) from exc

    @staticmethod
    def _validate_index(index):
        if not isinstance(index, CodeIndexResult):
            raise RelevantCodeRetrievalError(
                "Index must be a CodeIndexResult instance."
            )

        if not isinstance(index.entries, tuple):
            raise RelevantCodeRetrievalError(
                "Index entries must be a tuple."
            )

        if not all(
            isinstance(entry, CodeIndexEntry)
            for entry in index.entries
        ):
            raise RelevantCodeRetrievalError(
                "Index contains an invalid code entry."
            )

    @staticmethod
    def _validate_relevant_files(relevant_files):
        if not isinstance(
            relevant_files,
            RelevantFileRetrievalResult,
        ):
            raise RelevantCodeRetrievalError(
                "Relevant files must be a RelevantFileRetrievalResult."
            )

        if not isinstance(relevant_files.question, str):
            raise RelevantCodeRetrievalError(
                "Relevant files must contain a valid question."
            )

        if not isinstance(relevant_files.files, tuple):
            raise RelevantCodeRetrievalError(
                "Relevant files must be provided as a tuple."
            )

    @staticmethod
    def _validate_limit(limit):
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit <= 0
        ):
            raise RelevantCodeRetrievalError(
                "Limit must be a positive integer."
            )
