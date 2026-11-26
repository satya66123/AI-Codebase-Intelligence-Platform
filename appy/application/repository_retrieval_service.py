
"""Retrieve repository intelligence for an analyzed user question."""

from dataclasses import dataclass

from appy.application.question_analysis_agent import (
    QuestionAnalysisResult,
)
from appy.application.context_memory_retrieval_service import (
    ContextMemoryRetrievalError,
    ContextMemoryRetrievalService,
)
from appy.application.intent_detection_service import QueryIntent


class RepositoryRetrievalError(ValueError):
    """Raised when repository intelligence retrieval fails."""


@dataclass(frozen=True)
class RepositoryRetrievalResult:
    """Structured result of repository intelligence retrieval."""

    repository_id: str
    question: str
    intent: QueryIntent
    retrieval_data: object

    def __post_init__(self) -> None:
        if (
            not isinstance(self.repository_id, str)
            or not self.repository_id.strip()
        ):
            raise RepositoryRetrievalError(
                "Repository ID must be a non-empty string."
            )

        if (
            not isinstance(self.question, str)
            or not self.question.strip()
        ):
            raise RepositoryRetrievalError(
                "Question must be a non-empty string."
            )

        if not isinstance(self.intent, QueryIntent):
            raise RepositoryRetrievalError("Invalid query intent.")

        if self.retrieval_data is None:
            raise RepositoryRetrievalError(
                "Retrieval data cannot be None."
            )


class RepositoryRetrievalService:
    """
    Coordinate retrieval of repository intelligence.

    Workflow:
        Question Analysis Result
                 |
        Repository ID Validation
                 |
        Context Memory Retrieval
                 |
        Repository Retrieval Result
    """

    def __init__(
        self,
        memory_retrieval_service: ContextMemoryRetrievalService,
    ) -> None:
        if not callable(
            getattr(memory_retrieval_service, "retrieve", None)
        ):
            raise RepositoryRetrievalError(
                "Memory retrieval service must provide a retrieve method."
            )

        self.memory_retrieval_service = memory_retrieval_service

    def retrieve(
        self,
        repository_id: str,
        analysis_result: QuestionAnalysisResult,
        limit: int = 10,
    ) -> RepositoryRetrievalResult:
        """
        Retrieve relevant repository memories for an analyzed question.
        """

        if (
            not isinstance(repository_id, str)
            or not repository_id.strip()
        ):
            raise RepositoryRetrievalError(
                "Repository ID must be a non-empty string."
            )

        if not isinstance(analysis_result, QuestionAnalysisResult):
            raise RepositoryRetrievalError(
                "A valid QuestionAnalysisResult is required."
            )

        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
        ):
            raise RepositoryRetrievalError(
                "Retrieval limit must be a positive integer."
            )

        try:
            retrieval_data = self.memory_retrieval_service.retrieve(
                repository_id=repository_id,
                query=analysis_result.question,
                limit=limit,
            )

            return RepositoryRetrievalResult(
                repository_id=repository_id,
                question=analysis_result.question,
                intent=analysis_result.intent,
                retrieval_data=retrieval_data,
            )

        except ContextMemoryRetrievalError as exc:
            raise RepositoryRetrievalError(
                f"Repository memory retrieval failed: {exc}"
            ) from exc
        except RepositoryRetrievalError:
            raise
        except Exception as exc:
            raise RepositoryRetrievalError(
                f"Unexpected repository retrieval error: {exc}"
            ) from exc
