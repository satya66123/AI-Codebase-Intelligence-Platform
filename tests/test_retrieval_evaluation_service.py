
import pytest

from app.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexResult,
)
from app.application.retrieval_evaluation_service import (
    RetrievalEvaluationCase,
    RetrievalEvaluationError,
    RetrievalEvaluationService,
    RetrievalQueryEvaluation,
    RetrievalEvaluationResult,
)


def create_entry(
    entity_id,
    name,
    entity_type="function",
    filename="app.py",
):
    return CodeIndexEntry(
        entity_id=entity_id,
        name=name,
        entity_type=entity_type,
        qualified_name=name,
        filename=filename,
        line=1,
        end_line=5,
        parent=None,
        docstring=None,
        normalized_name=name.casefold(),
        search_text=(
            f"{name} {entity_type} {filename}"
        ).casefold(),
    )


def create_index(entries=None):
    if entries is None:
        entries = (
            create_entry("id-1", "create_user"),
            create_entry("id-2", "delete_user"),
            create_entry("id-3", "update_user"),
            create_entry(
                "id-4",
                "UserService",
                entity_type="class",
            ),
            create_entry(
                "id-5",
                "get_user",
                filename="users.py",
            ),
        )

    entries = tuple(entries)

    by_file = {}

    for entry in entries:
        by_file.setdefault(entry.filename, []).append(
            entry.entity_id
        )

    files = tuple(sorted(by_file))

    entity_counts = {}

    for entry in entries:
        entity_counts[entry.entity_type] = (
            entity_counts.get(entry.entity_type, 0) + 1
        )

    return CodeIndexResult(
        index_version=1,
        entries=entries,
        total_entities=len(entries),
        total_files=len(files),
        files=files,
        entity_counts=entity_counts,
        by_file={
            filename: tuple(entity_ids)
            for filename, entity_ids in by_file.items()
        },
    )


class StubSearchService:
    """Test double for the code search service."""

    def __init__(
        self,
        results=None,
        error=None,
    ):
        # Preserve None and other invalid values for validation tests.
        self.results = results
        self.error = error
        self.calls = []

    def search(
        self,
        index,
        query,
        entity_type=None,
        exact_match=False,
    ):
        self.calls.append(
            {
                "index": index,
                "query": query,
                "entity_type": entity_type,
                "exact_match": exact_match,
            }
        )

        if self.error is not None:
            raise self.error

        return self.results


def create_case(
    query="user",
    relevant_entity_ids=("id-1",),
    entity_type=None,
    exact_match=False,
    k=5,
):
    return RetrievalEvaluationCase(
        query=query,
        relevant_entity_ids=relevant_entity_ids,
        entity_type=entity_type,
        exact_match=exact_match,
        k=k,
    )


def test_evaluate_returns_result_for_one_query():
    index = create_index()

    search = StubSearchService(
        results=(index.entries[0],)
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (create_case(),),
    )

    assert isinstance(result, RetrievalEvaluationResult)
    assert result.total_queries == 1
    assert result.has_results is True
    assert len(result.query_results) == 1


def test_evaluate_calculates_perfect_metrics():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[0],
            index.entries[1],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1", "id-2"),
                k=2,
            ),
        ),
    )

    query_result = result.query_results[0]

    assert query_result.precision_at_k == 1.0
    assert query_result.recall_at_k == 1.0
    assert query_result.f1_at_k == 1.0
    assert query_result.reciprocal_rank_at_k == 1.0
    assert query_result.hit_at_k == 1.0


def test_evaluate_calculates_precision_at_k():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[0],
            index.entries[1],
            index.entries[2],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=3,
            ),
        ),
    )

    assert result.query_results[0].precision_at_k == pytest.approx(
        1 / 3
    )


def test_evaluate_calculates_recall_at_k():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[0],
            index.entries[1],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=(
                    "id-1",
                    "id-2",
                    "id-3",
                    "id-4",
                ),
                k=2,
            ),
        ),
    )

    assert result.query_results[0].recall_at_k == 0.5


def test_evaluate_calculates_f1_score():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[0],
            index.entries[1],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=(
                    "id-1",
                    "id-2",
                    "id-3",
                    "id-4",
                ),
                k=2,
            ),
        ),
    )

    query_result = result.query_results[0]

    assert query_result.precision_at_k == 1.0
    assert query_result.recall_at_k == 0.5
    assert query_result.f1_at_k == pytest.approx(2 / 3)


def test_evaluate_calculates_reciprocal_rank():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[1],
            index.entries[2],
            index.entries[0],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=3,
            ),
        ),
    )

    assert (
        result.query_results[0].reciprocal_rank_at_k
        == pytest.approx(1 / 3)
    )


def test_evaluate_returns_zero_reciprocal_rank_when_no_hit():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[1],
            index.entries[2],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=2,
            ),
        ),
    )

    assert (
        result.query_results[0].reciprocal_rank_at_k
        == 0.0
    )


def test_evaluate_calculates_hit_at_k():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[1],
            index.entries[0],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=2,
            ),
        ),
    )

    assert result.query_results[0].hit_at_k == 1.0


def test_evaluate_returns_zero_hit_when_no_relevant_result():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[1],
            index.entries[2],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=2,
            ),
        ),
    )

    assert result.query_results[0].hit_at_k == 0.0


def test_evaluate_limits_results_to_k():
    index = create_index()

    search = StubSearchService(
        results=tuple(index.entries)
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=2,
            ),
        ),
    )

    assert result.query_results[0].retrieved_count == 2
    assert result.query_results[0].retrieved_entity_ids == (
        "id-1",
        "id-2",
    )


def test_precision_uses_k_as_denominator_when_fewer_results_returned():
    index = create_index()

    search = StubSearchService(
        results=(index.entries[0],)
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=5,
            ),
        ),
    )

    assert result.query_results[0].precision_at_k == 0.2


def test_empty_search_results_produce_zero_metrics():
    index = create_index()

    search = StubSearchService(results=())

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (create_case(),),
    )

    query_result = result.query_results[0]

    assert query_result.retrieved_count == 0
    assert query_result.precision_at_k == 0.0
    assert query_result.recall_at_k == 0.0
    assert query_result.f1_at_k == 0.0
    assert query_result.reciprocal_rank_at_k == 0.0
    assert query_result.hit_at_k == 0.0


def test_evaluate_calculates_aggregate_metrics():
    index = create_index()

    search = StubSearchService(
        results=(index.entries[0],)
    )

    service = RetrievalEvaluationService(search)

    cases = (
        create_case(
            query="first",
            relevant_entity_ids=("id-1",),
            k=1,
        ),
        create_case(
            query="second",
            relevant_entity_ids=("id-2",),
            k=1,
        ),
    )

    result = service.evaluate(index, cases)

    assert result.total_queries == 2
    assert result.mean_precision_at_k == 0.5
    assert result.mean_recall_at_k == 0.5
    assert result.mean_f1_at_k == 0.5
    assert result.mean_reciprocal_rank_at_k == 0.5
    assert result.hit_rate_at_k == 0.5


def test_evaluate_calculates_average_retrieved_count():
    index = create_index()

    class DifferentResultSearch:
        def __init__(self):
            self.calls = 0

        def search(
            self,
            index,
            query,
            entity_type=None,
            exact_match=False,
        ):
            self.calls += 1

            if self.calls == 1:
                return (index.entries[0], index.entries[1])

            return (index.entries[0],)

    service = RetrievalEvaluationService(
        DifferentResultSearch()
    )

    result = service.evaluate(
        index,
        (
            create_case(query="first", k=2),
            create_case(query="second", k=2),
        ),
    )

    assert result.total_retrieved_entities == 3
    assert result.average_retrieved_count == 1.5


def test_evaluate_passes_search_parameters():
    index = create_index()

    search = StubSearchService(
        results=(index.entries[0],)
    )

    service = RetrievalEvaluationService(search)

    service.evaluate(
        index,
        (
            create_case(
                query="create_user",
                entity_type="function",
                exact_match=True,
            ),
        ),
    )

    assert len(search.calls) == 1
    assert search.calls[0]["query"] == "create_user"
    assert search.calls[0]["entity_type"] == "function"
    assert search.calls[0]["exact_match"] is True


def test_evaluate_accepts_generator_of_cases():
    index = create_index()

    search = StubSearchService(
        results=(index.entries[0],)
    )

    service = RetrievalEvaluationService(search)

    cases = (
        create_case(query=f"query-{number}")
        for number in range(2)
    )

    result = service.evaluate(index, cases)

    assert result.total_queries == 2


def test_evaluate_rejects_invalid_index():
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="CodeIndexResult",
    ):
        service.evaluate(
            None,
            (create_case(),),
        )


def test_evaluate_rejects_index_with_invalid_entries():
    index = CodeIndexResult(
        index_version=1,
        entries=("invalid",),
        total_entities=1,
        total_files=0,
        files=(),
        entity_counts={},
        by_file={},
    )

    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="invalid code entries",
    ):
        service.evaluate(
            index,
            (create_case(),),
        )


@pytest.mark.parametrize(
    "evaluation_cases",
    [
        None,
        "invalid",
        b"invalid",
        {"query": "user"},
        123,
    ],
)
def test_evaluate_rejects_invalid_case_collections(
    evaluation_cases,
):
    service = RetrievalEvaluationService()

    with pytest.raises(RetrievalEvaluationError):
        service.evaluate(
            create_index(),
            evaluation_cases,
        )


def test_evaluate_rejects_empty_case_collection():
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="At least one evaluation case",
    ):
        service.evaluate(create_index(), ())


def test_evaluate_rejects_invalid_case_item():
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="RetrievalEvaluationCase",
    ):
        service.evaluate(
            create_index(),
            ("invalid",),
        )


@pytest.mark.parametrize(
    "query",
    [
        "",
        " ",
        None,
        123,
    ],
)
def test_evaluate_rejects_invalid_query(query):
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="query must be a non-empty string",
    ):
        service.evaluate(
            create_index(),
            (
                create_case(query=query),
            ),
        )


@pytest.mark.parametrize(
    "relevant_entity_ids",
    [
        (),
        [],
        "id-1",
        ("",),
        (None,),
        (123,),
        ("id-1", "id-1"),
    ],
)
def test_evaluate_rejects_invalid_relevant_entity_ids(
    relevant_entity_ids,
):
    service = RetrievalEvaluationService()

    with pytest.raises(RetrievalEvaluationError):
        service.evaluate(
            create_index(),
            (
                RetrievalEvaluationCase(
                    query="user",
                    relevant_entity_ids=relevant_entity_ids,
                ),
            ),
        )


@pytest.mark.parametrize(
    "entity_type",
    [
        "",
        " ",
        123,
    ],
)
def test_evaluate_rejects_invalid_entity_type(entity_type):
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="Entity type",
    ):
        service.evaluate(
            create_index(),
            (
                create_case(entity_type=entity_type),
            ),
        )


@pytest.mark.parametrize(
    "exact_match",
    [
        "true",
        1,
        None,
    ],
)
def test_evaluate_rejects_invalid_exact_match(exact_match):
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="exact_match",
    ):
        service.evaluate(
            create_index(),
            (
                create_case(exact_match=exact_match),
            ),
        )


@pytest.mark.parametrize(
    "k",
    [
        0,
        -1,
        1.5,
        True,
        "5",
        None,
    ],
)
def test_evaluate_rejects_invalid_k(k):
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="K must be a positive integer",
    ):
        service.evaluate(
            create_index(),
            (
                create_case(k=k),
            ),
        )


def test_evaluate_rejects_relevant_ids_missing_from_index():
    service = RetrievalEvaluationService()

    with pytest.raises(
        RetrievalEvaluationError,
        match="missing from the index",
    ):
        service.evaluate(
            create_index(),
            (
                create_case(
                    relevant_entity_ids=("unknown-id",),
                ),
            ),
        )


def test_evaluate_wraps_search_service_errors():
    index = create_index()

    search = StubSearchService(
        error=RuntimeError("Search failed")
    )

    service = RetrievalEvaluationService(search)

    with pytest.raises(
        RetrievalEvaluationError,
        match="Retrieval failed",
    ):
        service.evaluate(
            index,
            (create_case(),),
        )


@pytest.mark.parametrize(
    "invalid_results",
    [
        None,
        [],
        "invalid",
        ("invalid-entry",),
    ],
)
def test_evaluate_rejects_invalid_search_results(
    invalid_results,
):
    index = create_index()

    search = StubSearchService(
        results=invalid_results
    )

    service = RetrievalEvaluationService(search)

    with pytest.raises(RetrievalEvaluationError):
        service.evaluate(
            index,
            (create_case(),),
        )


def test_constructor_rejects_invalid_search_service():
    with pytest.raises(
        RetrievalEvaluationError,
        match="callable search method",
    ):
        RetrievalEvaluationService(
            search_service=object()
        )


def test_query_result_contains_retrieved_and_relevant_ids():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[1],
            index.entries[0],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1",),
                k=2,
            ),
        ),
    )

    query_result = result.query_results[0]

    assert isinstance(
        query_result,
        RetrievalQueryEvaluation,
    )
    assert query_result.retrieved_entity_ids == (
        "id-2",
        "id-1",
    )
    assert query_result.relevant_entity_ids == ("id-1",)


def test_evaluate_handles_multiple_relevant_results():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[0],
            index.entries[1],
            index.entries[2],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1", "id-3"),
                k=3,
            ),
        ),
    )

    query_result = result.query_results[0]

    assert query_result.relevant_retrieved_count == 2
    assert query_result.precision_at_k == pytest.approx(2 / 3)
    assert query_result.recall_at_k == 1.0
    assert query_result.reciprocal_rank_at_k == 1.0


def test_evaluate_does_not_mutate_index():
    index = create_index()
    original_entries = index.entries

    search = StubSearchService(
        results=(index.entries[0],)
    )

    service = RetrievalEvaluationService(search)

    service.evaluate(
        index,
        (create_case(),),
    )

    assert index.entries is original_entries


def test_evaluate_result_reports_total_entity_counts():
    index = create_index()

    search = StubSearchService(
        results=(
            index.entries[0],
            index.entries[1],
        )
    )

    service = RetrievalEvaluationService(search)

    result = service.evaluate(
        index,
        (
            create_case(
                relevant_entity_ids=("id-1", "id-2"),
                k=2,
            ),
        ),
    )

    assert result.total_relevant_entities == 2
    assert result.total_retrieved_entities == 2


def test_evaluate_result_has_results_property():
    index = create_index()

    search = StubSearchService(
        results=(index.entries[0],)
    )

    result = RetrievalEvaluationService(search).evaluate(
        index,
        (create_case(),),
    )

    assert result.has_results is True
