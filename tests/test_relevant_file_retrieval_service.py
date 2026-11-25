
import pytest

from app.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexResult,
)
from app.application.code_search_service import CodeSearchService
from app.application.intent_detection_service import QueryIntent
from app.application.question_analysis_agent import (
    QuestionAnalysisResult,
)
from app.application.relevant_file_retrieval_service import (
    RelevantFile,
    RelevantFileRetrievalError,
    RelevantFileRetrievalResult,
    RelevantFileRetrievalService,
)


QUESTION = "Where is authentication implemented?"


def create_entry(
    entity_id,
    name,
    filename,
    search_text,
    entity_type="function",
):
    """Create a valid searchable code index entry."""
    return CodeIndexEntry(
        entity_id=entity_id,
        name=name,
        entity_type=entity_type,
        qualified_name=name,
        filename=filename,
        line=1,
        end_line=10,
        parent=None,
        docstring="Test documentation.",
        normalized_name=name.casefold(),
        search_text=search_text.casefold(),
    )


@pytest.fixture
def analysis_result():
    """Provide a valid question analysis result."""
    return QuestionAnalysisResult(
        question=QUESTION,
        intent=QueryIntent.CODE_EXPLANATION,
        confidence=0.9,
        matched_terms=("authentication",),
    )


@pytest.fixture
def index():
    """Build an index using the actual CodeIndexResult structure."""
    entries = (
        create_entry(
            "entity-1",
            "authenticate_user",
            "app/auth.py",
            f"authenticate_user {QUESTION} authentication",
        ),
        create_entry(
            "entity-2",
            "login",
            "app/login.py",
            f"login {QUESTION} authentication",
        ),
        create_entry(
            "entity-3",
            "process_payment",
            "app/payment.py",
            "process_payment payment processing",
        ),
    )

    return CodeIndexResult(
        index_version=1,
        entries=entries,
        total_entities=len(entries),
        total_files=3,
        files=(
            "app/auth.py",
            "app/login.py",
            "app/payment.py",
        ),
        entity_counts={
            "function": 3,
        },
        by_file={
            "app/auth.py": ("entity-1",),
            "app/login.py": ("entity-2",),
            "app/payment.py": ("entity-3",),
        },
    )


@pytest.fixture
def service():
    return RelevantFileRetrievalService()


# ---------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------


def test_service_initialization():
    service = RelevantFileRetrievalService()

    assert service is not None


def test_service_uses_default_code_search_service():
    service = RelevantFileRetrievalService()

    assert isinstance(service.code_search_service, CodeSearchService)


def test_service_accepts_custom_code_search_service():
    search_service = CodeSearchService()

    service = RelevantFileRetrievalService(
        code_search_service=search_service
    )

    assert service.code_search_service is search_service


def test_service_rejects_invalid_search_service():
    with pytest.raises(RelevantFileRetrievalError):
        RelevantFileRetrievalService(
            code_search_service="invalid"
        )


# ---------------------------------------------------------
# RelevantFile model tests
# ---------------------------------------------------------


def test_relevant_file_creation(index):
    entry = index.entries[0]

    result = RelevantFile(
        filename=entry.filename,
        relevance_score=1,
        matched_entities=(entry,),
    )

    assert result.filename == "app/auth.py"
    assert result.relevance_score == 1
    assert result.matched_entities == (entry,)


def test_relevant_file_rejects_empty_filename(index):
    with pytest.raises((ValueError, RelevantFileRetrievalError)):
        RelevantFile(
            filename="",
            relevance_score=1,
            matched_entities=(index.entries[0],),
        )


def test_relevant_file_rejects_invalid_score(index):
    with pytest.raises((ValueError, RelevantFileRetrievalError)):
        RelevantFile(
            filename="app/auth.py",
            relevance_score=-1,
            matched_entities=(index.entries[0],),
        )


def test_relevant_file_rejects_score_not_matching_entities(index):
    with pytest.raises((ValueError, RelevantFileRetrievalError)):
        RelevantFile(
            filename="app/auth.py",
            relevance_score=2,
            matched_entities=(index.entries[0],),
        )


def test_relevant_file_rejects_invalid_matched_entities():
    with pytest.raises((ValueError, RelevantFileRetrievalError)):
        RelevantFile(
            filename="app/auth.py",
            relevance_score=1,
            matched_entities=("invalid",),
        )


# ---------------------------------------------------------
# Retrieval result model tests
# ---------------------------------------------------------


def test_retrieval_result_creation(index):
    entry = index.entries[0]

    file_result = RelevantFile(
        filename=entry.filename,
        relevance_score=1,
        matched_entities=(entry,),
    )

    result = RelevantFileRetrievalResult(
        question=QUESTION,
        total_files=1,
        files=(file_result,),
    )

    assert result.question == QUESTION
    assert result.total_files == 1
    assert len(result.files) == 1


def test_retrieval_result_supports_empty_files():
    result = RelevantFileRetrievalResult(
        question=QUESTION,
        total_files=0,
        files=(),
    )

    assert result.total_files == 0
    assert result.files == ()


# ---------------------------------------------------------
# Main retrieval tests
# ---------------------------------------------------------


def test_retrieve_returns_result(service, index, analysis_result):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    assert isinstance(result, RelevantFileRetrievalResult)


def test_retrieve_preserves_question(service, index, analysis_result):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    assert result.question == QUESTION


def test_retrieve_returns_matching_files(
    service,
    index,
    analysis_result,
):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    filenames = {item.filename for item in result.files}

    assert "app/auth.py" in filenames
    assert "app/login.py" in filenames


def test_retrieve_excludes_unrelated_files(
    service,
    index,
    analysis_result,
):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    filenames = {item.filename for item in result.files}

    assert "app/payment.py" not in filenames


def test_retrieve_groups_entities_by_filename(
    service,
    index,
    analysis_result,
):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    for file_result in result.files:
        assert all(
            entry.filename == file_result.filename
            for entry in file_result.matched_entities
        )


def test_retrieve_calculates_relevance_score(
    service,
    index,
    analysis_result,
):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    for file_result in result.files:
        assert file_result.relevance_score == len(
            file_result.matched_entities
        )


def test_retrieve_reports_total_files(
    service,
    index,
    analysis_result,
):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    assert result.total_files == len(result.files)


def test_retrieve_respects_limit(
    service,
    index,
    analysis_result,
):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
        limit=1,
    )

    assert len(result.files) <= 1


def test_retrieve_with_larger_limit(
    service,
    index,
    analysis_result,
):
    result = service.retrieve(
        index=index,
        analysis_result=analysis_result,
        limit=20,
    )

    assert len(result.files) <= 20


def test_retrieve_rejects_zero_limit(
    service,
    index,
    analysis_result,
):
    with pytest.raises(RelevantFileRetrievalError):
        service.retrieve(
            index=index,
            analysis_result=analysis_result,
            limit=0,
        )


def test_retrieve_rejects_negative_limit(
    service,
    index,
    analysis_result,
):
    with pytest.raises(RelevantFileRetrievalError):
        service.retrieve(
            index=index,
            analysis_result=analysis_result,
            limit=-1,
        )


def test_retrieve_rejects_invalid_index(
    service,
    analysis_result,
):
    with pytest.raises(RelevantFileRetrievalError):
        service.retrieve(
            index="invalid",
            analysis_result=analysis_result,
        )


def test_retrieve_rejects_none_index(
    service,
    analysis_result,
):
    with pytest.raises(RelevantFileRetrievalError):
        service.retrieve(
            index=None,
            analysis_result=analysis_result,
        )


def test_retrieve_rejects_invalid_analysis_result(
    service,
    index,
):
    with pytest.raises(RelevantFileRetrievalError):
        service.retrieve(
            index=index,
            analysis_result="invalid",
        )


def test_retrieve_rejects_none_analysis_result(
    service,
    index,
):
    with pytest.raises(RelevantFileRetrievalError):
        service.retrieve(
            index=index,
            analysis_result=None,
        )


# ---------------------------------------------------------
# Empty index and no-match tests
# ---------------------------------------------------------


def test_retrieve_from_empty_index(
    service,
    analysis_result,
):
    empty_index = CodeIndexResult(
        index_version=1,
        entries=(),
        total_entities=0,
        total_files=0,
        files=(),
        entity_counts={},
        by_file={},
    )

    result = service.retrieve(
        index=empty_index,
        analysis_result=analysis_result,
    )

    assert isinstance(result, RelevantFileRetrievalResult)
    assert result.total_files == 0
    assert result.files == ()


def test_retrieve_returns_empty_result_when_nothing_matches(
    service,
    analysis_result,
):
    unrelated_entry = create_entry(
        "entity-10",
        "calculate_tax",
        "app/tax.py",
        "calculate tax financial report",
    )

    unrelated_index = CodeIndexResult(
        index_version=1,
        entries=(unrelated_entry,),
        total_entities=1,
        total_files=1,
        files=("app/tax.py",),
        entity_counts={"function": 1},
        by_file={
            "app/tax.py": (unrelated_entry.entity_id,),
        },
    )

    result = service.retrieve(
        index=unrelated_index,
        analysis_result=analysis_result,
    )

    assert result.total_files == 0
    assert result.files == ()


# ---------------------------------------------------------
# Ranking and ordering tests
# ---------------------------------------------------------


def test_retrieve_orders_results_deterministically(
    service,
    index,
    analysis_result,
):
    first = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    second = service.retrieve(
        index=index,
        analysis_result=analysis_result,
    )

    assert [
        item.filename for item in first.files
    ] == [
        item.filename for item in second.files
    ]


def test_retrieve_orders_by_relevance_score(
    service,
    analysis_result,
):
    entries = (
        create_entry(
            "entity-1",
            "authenticate_user",
            "app/auth.py",
            f"authenticate_user {QUESTION} authentication",
        ),
        create_entry(
            "entity-2",
            "validate_user",
            "app/auth.py",
            f"validate_user {QUESTION} authentication",
        ),
        create_entry(
            "entity-3",
            "login",
            "app/login.py",
            f"login {QUESTION} authentication",
        ),
    )

    custom_index = CodeIndexResult(
        index_version=1,
        entries=entries,
        total_entities=3,
        total_files=2,
        files=("app/auth.py", "app/login.py"),
        entity_counts={"function": 3},
        by_file={
            "app/auth.py": ("entity-1", "entity-2"),
            "app/login.py": ("entity-3",),
        },
    )

    result = RelevantFileRetrievalService().retrieve(
        index=custom_index,
        analysis_result=analysis_result,
    )

    assert result.files[0].filename == "app/auth.py"
    assert result.files[0].relevance_score == 2


def test_retrieve_uses_filename_as_deterministic_tiebreaker(
    service,
    analysis_result,
):
    entries = (
        create_entry(
            "entity-1",
            "authenticate_user",
            "app/z_auth.py",
            f"authenticate_user {QUESTION}",
        ),
        create_entry(
            "entity-2",
            "login",
            "app/a_auth.py",
            f"login {QUESTION}",
        ),
    )

    custom_index = CodeIndexResult(
        index_version=1,
        entries=entries,
        total_entities=2,
        total_files=2,
        files=("app/a_auth.py", "app/z_auth.py"),
        entity_counts={"function": 2},
        by_file={
            "app/z_auth.py": ("entity-1",),
            "app/a_auth.py": ("entity-2",),
        },
    )

    result = service.retrieve(
        index=custom_index,
        analysis_result=analysis_result,
    )

    filenames = [item.filename for item in result.files]

    assert filenames == sorted(filenames)
