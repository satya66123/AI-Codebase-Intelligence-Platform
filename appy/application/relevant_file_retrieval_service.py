
"""Retrieve and rank relevant source files for a codebase question."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Tuple

from appy.application.code_search_service import (
    CodeSearchError,
    CodeSearchService,
)
from appy.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexResult,
)
from appy.application.question_analysis_agent import (
    QuestionAnalysisResult,
)


class RelevantFileRetrievalError(Exception):
    """Raised when relevant file retrieval fails."""


@dataclass(frozen=True)
class RelevantFile:
    """A source file and its matched code entities."""

    filename: str
    relevance_score: int
    matched_entities: Tuple[CodeIndexEntry, ...]

    def __post_init__(self):
        if not isinstance(self.filename, str) or not self.filename.strip():
            raise RelevantFileRetrievalError(
                "Filename must be a non-empty string."
            )

        if (
            not isinstance(self.relevance_score, int)
            or isinstance(self.relevance_score, bool)
            or self.relevance_score < 0
        ):
            raise RelevantFileRetrievalError(
                "Relevance score must be a non-negative integer."
            )

        if not isinstance(self.matched_entities, tuple):
            raise RelevantFileRetrievalError(
                "Matched entities must be a tuple."
            )

        if not self.matched_entities:
            raise RelevantFileRetrievalError(
                "Matched entities cannot be empty."
            )

        if not all(
            isinstance(entity, CodeIndexEntry)
            for entity in self.matched_entities
        ):
            raise RelevantFileRetrievalError(
                "Every matched entity must be a CodeIndexEntry."
            )

        if self.relevance_score != len(self.matched_entities):
            raise RelevantFileRetrievalError(
                "Relevance score must equal the number of matched entities."
            )


@dataclass(frozen=True)
class RelevantFileRetrievalResult:
    """Result returned by relevant file retrieval."""

    question: str
    total_files: int
    files: Tuple[RelevantFile, ...]

    def __post_init__(self):
        if not isinstance(self.question, str) or not self.question.strip():
            raise RelevantFileRetrievalError(
                "Question must be a non-empty string."
            )

        if (
            not isinstance(self.total_files, int)
            or isinstance(self.total_files, bool)
            or self.total_files < 0
        ):
            raise RelevantFileRetrievalError(
                "Total files must be a non-negative integer."
            )

        if not isinstance(self.files, tuple):
            raise RelevantFileRetrievalError(
                "Files must be a tuple."
            )

        if not all(isinstance(item, RelevantFile) for item in self.files):
            raise RelevantFileRetrievalError(
                "Every file must be a RelevantFile."
            )

        if self.total_files != len(self.files):
            raise RelevantFileRetrievalError(
                "Total files must match the number of returned files."
            )


class RelevantFileRetrievalService:
    """Find source files relevant to a repository question."""

    def __init__(self, code_search_service=None):
        if code_search_service is not None and not isinstance(
            code_search_service, CodeSearchService
        ):
            raise RelevantFileRetrievalError(
                "code_search_service must be a CodeSearchService instance."
            )

        self.code_search_service = (
            code_search_service or CodeSearchService()
        )

    def retrieve(self, index, analysis_result, limit=10):
        """
        Retrieve relevant files from a code index.

        Files are grouped by filename and ranked by the number of
        matching code entities.
        """

        self._validate_index(index)
        self._validate_analysis_result(analysis_result)
        self._validate_limit(limit)

        question = analysis_result.question

        try:
            matched_entries = self.code_search_service.search(
                index=index,
                query=question,
            )
        except CodeSearchError as exc:
            raise RelevantFileRetrievalError(
                f"Code search failed: {exc}"
            ) from exc
        except Exception as exc:
            raise RelevantFileRetrievalError(
                f"Relevant file retrieval failed: {exc}"
            ) from exc

        grouped_entries = self._group_entries_by_file(matched_entries)

        relevant_files = [
            RelevantFile(
                filename=filename,
                relevance_score=len(entities),
                matched_entities=tuple(entities),
            )
            for filename, entities in grouped_entries.items()
        ]

        relevant_files.sort(
            key=lambda item: (
                -item.relevance_score,
                item.filename.casefold(),
            )
        )

        selected_files = tuple(relevant_files[:limit])

        return RelevantFileRetrievalResult(
            question=question,
            total_files=len(selected_files),
            files=selected_files,
        )

    @staticmethod
    def _validate_index(index):
        if not isinstance(index, CodeIndexResult):
            raise RelevantFileRetrievalError(
                "index must be a CodeIndexResult instance."
            )

    @staticmethod
    def _validate_analysis_result(analysis_result):
        if not isinstance(analysis_result, QuestionAnalysisResult):
            raise RelevantFileRetrievalError(
                "analysis_result must be a QuestionAnalysisResult instance."
            )

        if (
            not isinstance(analysis_result.question, str)
            or not analysis_result.question.strip()
        ):
            raise RelevantFileRetrievalError(
                "Analysis result must contain a valid question."
            )

    @staticmethod
    def _validate_limit(limit):
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit <= 0
        ):
            raise RelevantFileRetrievalError(
                "Limit must be a positive integer."
            )

    @staticmethod
    def _group_entries_by_file(entries):
        grouped = {}

        for entry in entries:
            if not isinstance(entry, CodeIndexEntry):
                raise RelevantFileRetrievalError(
                    "Search results must contain CodeIndexEntry objects."
                )

            normalized_filename = str(
                PurePosixPath(entry.filename.replace("\\", "/"))
            )

            grouped.setdefault(normalized_filename, []).append(entry)

        return grouped
