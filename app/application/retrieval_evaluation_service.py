
from dataclasses import dataclass
from typing import Iterable

from app.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexResult,
)
from app.application.code_search_service import (
    CodeSearchService,
)


class RetrievalEvaluationError(ValueError):
    """Raised when retrieval evaluation fails."""


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    """Defines one retrieval query and its expected relevant entities."""

    query: str
    relevant_entity_ids: tuple
    entity_type: str | None = None
    exact_match: bool = False
    k: int = 5


@dataclass(frozen=True)
class RetrievalQueryEvaluation:
    """Contains retrieval metrics for one evaluation query."""

    query: str
    relevant_count: int
    retrieved_count: int
    relevant_retrieved_count: int
    precision_at_k: float
    recall_at_k: float
    f1_at_k: float
    reciprocal_rank_at_k: float
    hit_at_k: float
    retrieved_entity_ids: tuple
    relevant_entity_ids: tuple


@dataclass(frozen=True)
class RetrievalEvaluationResult:
    """Contains aggregate retrieval evaluation metrics."""

    total_queries: int
    total_relevant_entities: int
    total_retrieved_entities: int
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_f1_at_k: float
    mean_reciprocal_rank_at_k: float
    hit_rate_at_k: float
    query_results: tuple

    @property
    def has_results(self) -> bool:
        """Return whether the evaluation contains query results."""
        return bool(self.query_results)

    @property
    def average_retrieved_count(self) -> float:
        """Return the average number of retrieved entries per query."""
        if not self.total_queries:
            return 0.0

        return self.total_retrieved_entities / self.total_queries


class RetrievalEvaluationService:
    """Evaluate code retrieval quality using known relevant entity IDs."""

    def __init__(
        self,
        search_service: CodeSearchService | None = None,
    ):
        self.search_service = (
            search_service
            if search_service is not None
            else CodeSearchService()
        )

        if not callable(
            getattr(self.search_service, "search", None)
        ):
            raise RetrievalEvaluationError(
                "Search service must provide a callable search method."
            )

    def evaluate(
        self,
        index: CodeIndexResult,
        evaluation_cases: Iterable[RetrievalEvaluationCase],
    ) -> RetrievalEvaluationResult:
        """Evaluate retrieval performance across multiple test queries."""

        self._validate_index(index)
        cases = self._validate_cases(evaluation_cases)

        if not cases:
            raise RetrievalEvaluationError(
                "At least one evaluation case is required."
            )

        index_entity_ids = {
            entry.entity_id
            for entry in index.entries
        }

        query_results = []

        for case in cases:
            self._validate_relevant_entities(
                case,
                index_entity_ids,
            )

            try:
                retrieved_entries = self.search_service.search(
                    index=index,
                    query=case.query,
                    entity_type=case.entity_type,
                    exact_match=case.exact_match,
                )
            except Exception as exc:
                raise RetrievalEvaluationError(
                    f"Retrieval failed for query '{case.query}': {exc}"
                ) from exc

            self._validate_retrieved_entries(retrieved_entries)

            query_results.append(
                self._evaluate_case(
                    case=case,
                    retrieved_entries=retrieved_entries,
                )
            )

        return self._create_result(tuple(query_results))

    @staticmethod
    def _validate_index(index: CodeIndexResult) -> None:
        """Validate the code index before evaluation."""

        if not isinstance(index, CodeIndexResult):
            raise RetrievalEvaluationError(
                "Index must be a CodeIndexResult instance."
            )

        if not isinstance(index.entries, tuple):
            raise RetrievalEvaluationError(
                "Index entries must be a tuple."
            )

        if not all(
            isinstance(entry, CodeIndexEntry)
            for entry in index.entries
        ):
            raise RetrievalEvaluationError(
                "Index contains invalid code entries."
            )

    @staticmethod
    def _validate_cases(
        evaluation_cases: Iterable[RetrievalEvaluationCase],
    ) -> tuple:
        """Validate and materialize evaluation cases."""

        if evaluation_cases is None or isinstance(
            evaluation_cases,
            (str, bytes, dict),
        ):
            raise RetrievalEvaluationError(
                "Evaluation cases must be an iterable of evaluation cases."
            )

        try:
            cases = tuple(evaluation_cases)
        except TypeError as exc:
            raise RetrievalEvaluationError(
                "Evaluation cases must be iterable."
            ) from exc

        for case in cases:
            if not isinstance(case, RetrievalEvaluationCase):
                raise RetrievalEvaluationError(
                    "Every evaluation item must be a "
                    "RetrievalEvaluationCase instance."
                )

            RetrievalEvaluationService._validate_case(case)

        return cases

    @staticmethod
    def _validate_case(
        case: RetrievalEvaluationCase,
    ) -> None:
        """Validate one retrieval evaluation case."""

        if (
            not isinstance(case.query, str)
            or not case.query.strip()
        ):
            raise RetrievalEvaluationError(
                "Evaluation query must be a non-empty string."
            )

        if not isinstance(case.relevant_entity_ids, tuple):
            raise RetrievalEvaluationError(
                "Relevant entity IDs must be provided as a tuple."
            )

        if not case.relevant_entity_ids:
            raise RetrievalEvaluationError(
                "Each evaluation case must contain relevant entity IDs."
            )

        if not all(
            isinstance(entity_id, str) and entity_id.strip()
            for entity_id in case.relevant_entity_ids
        ):
            raise RetrievalEvaluationError(
                "Relevant entity IDs must be non-empty strings."
            )

        if len(set(case.relevant_entity_ids)) != len(
            case.relevant_entity_ids
        ):
            raise RetrievalEvaluationError(
                "Relevant entity IDs must not contain duplicates."
            )

        if case.entity_type is not None:
            if (
                not isinstance(case.entity_type, str)
                or not case.entity_type.strip()
            ):
                raise RetrievalEvaluationError(
                    "Entity type must be a non-empty string."
                )

        if not isinstance(case.exact_match, bool):
            raise RetrievalEvaluationError(
                "exact_match must be a boolean."
            )

        if (
            isinstance(case.k, bool)
            or not isinstance(case.k, int)
            or case.k < 1
        ):
            raise RetrievalEvaluationError(
                "K must be a positive integer."
            )

    @staticmethod
    def _validate_relevant_entities(
        case: RetrievalEvaluationCase,
        index_entity_ids: set,
    ) -> None:
        """Ensure ground-truth IDs exist in the evaluated index."""

        missing_ids = tuple(
            entity_id
            for entity_id in case.relevant_entity_ids
            if entity_id not in index_entity_ids
        )

        if missing_ids:
            raise RetrievalEvaluationError(
                "Relevant entity IDs are missing from the index: "
                + ", ".join(missing_ids)
            )

    @staticmethod
    def _validate_retrieved_entries(
        retrieved_entries,
    ) -> None:
        """Validate the output returned by the search service."""

        if not isinstance(retrieved_entries, tuple):
            raise RetrievalEvaluationError(
                "Search service must return a tuple of code index entries."
            )

        if not all(
            isinstance(entry, CodeIndexEntry)
            for entry in retrieved_entries
        ):
            raise RetrievalEvaluationError(
                "Search service returned invalid code index entries."
            )

    @staticmethod
    def _evaluate_case(
        case: RetrievalEvaluationCase,
        retrieved_entries: tuple,
    ) -> RetrievalQueryEvaluation:
        """Calculate ranking and relevance metrics for one query."""

        top_entries = retrieved_entries[:case.k]

        retrieved_ids = tuple(
            entry.entity_id
            for entry in top_entries
        )

        relevant_ids = set(case.relevant_entity_ids)
        relevant_retrieved_count = sum(
            entity_id in relevant_ids
            for entity_id in retrieved_ids
        )

        precision = relevant_retrieved_count / case.k
        recall = (
            relevant_retrieved_count
            / len(case.relevant_entity_ids)
        )

        if precision + recall:
            f1 = (
                2 * precision * recall
                / (precision + recall)
            )
        else:
            f1 = 0.0

        reciprocal_rank = 0.0

        for rank, entity_id in enumerate(
            retrieved_ids,
            start=1,
        ):
            if entity_id in relevant_ids:
                reciprocal_rank = 1.0 / rank
                break

        hit = (
            1.0
            if relevant_retrieved_count > 0
            else 0.0
        )

        return RetrievalQueryEvaluation(
            query=case.query,
            relevant_count=len(case.relevant_entity_ids),
            retrieved_count=len(retrieved_ids),
            relevant_retrieved_count=relevant_retrieved_count,
            precision_at_k=precision,
            recall_at_k=recall,
            f1_at_k=f1,
            reciprocal_rank_at_k=reciprocal_rank,
            hit_at_k=hit,
            retrieved_entity_ids=retrieved_ids,
            relevant_entity_ids=case.relevant_entity_ids,
        )

    @staticmethod
    def _create_result(
        query_results: tuple,
    ) -> RetrievalEvaluationResult:
        """Calculate aggregate metrics across all evaluation queries."""

        total_queries = len(query_results)

        if not total_queries:
            raise RetrievalEvaluationError(
                "Cannot create an evaluation result without query results."
            )

        total_relevant = sum(
            result.relevant_count
            for result in query_results
        )

        total_retrieved = sum(
            result.retrieved_count
            for result in query_results
        )

        return RetrievalEvaluationResult(
            total_queries=total_queries,
            total_relevant_entities=total_relevant,
            total_retrieved_entities=total_retrieved,
            mean_precision_at_k=(
                sum(
                    result.precision_at_k
                    for result in query_results
                )
                / total_queries
            ),
            mean_recall_at_k=(
                sum(
                    result.recall_at_k
                    for result in query_results
                )
                / total_queries
            ),
            mean_f1_at_k=(
                sum(
                    result.f1_at_k
                    for result in query_results
                )
                / total_queries
            ),
            mean_reciprocal_rank_at_k=(
                sum(
                    result.reciprocal_rank_at_k
                    for result in query_results
                )
                / total_queries
            ),
            hit_rate_at_k=(
                sum(
                    result.hit_at_k
                    for result in query_results
                )
                / total_queries
            ),
            query_results=query_results,
        )
