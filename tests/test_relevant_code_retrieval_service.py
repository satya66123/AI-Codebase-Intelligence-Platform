
import pytest

from app.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexResult,
)
from app.application.relevant_file_retrieval_service import (
    RelevantFile,
    RelevantFileRetrievalResult,
)
from app.application.relevant_code_retrieval_service import (
    RelevantCodeRetrievalError,
    RelevantCodeRetrievalResult,
    RelevantCodeRetrievalService,
)


QUESTION = "Where is authentication implemented?"


def create_entry(
    entity_id,
    name,
    filename,
    line=1,
    entity_type="function",
):
    return CodeIndexEntry(
        entity_id=entity_id,
        name=name,
        entity_type=entity_type,
        qualified_name=name,
        filename=filename,
        line=line,
        end_line=line + 5,
        parent=None,
        docstring="Test documentation.",
        normalized_name=name.casefold(),
        search_text=f"{name} {filename}".casefold(),
    )


@pytest.fixture
def index():
    entries = (
        create_entry(
            "entity-1",
            "authenticate_user",
            "app/auth.py",
            10,
        ),
        create_entry(
            "entity-2",
            "validate_user",
            "app/auth.py",
            20,
        ),
        create_entry(
            "entity-3",
            "login",
            "app/login.py",
            5,
        ),
        create_entry(
            "entity-4",
            "process_payment",
            "app/payment.py",
            15,
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
            "function": 4,
        },
        by_file={
            "app/auth.py": ("entity-1", "entity-2"),
            "app/login.py": ("entity-3",),
            "app/payment.py": ("entity-4",),
        },
    )


@pytest.fixture
def relevant_files(index):
    auth_entry = index.entries[0]
    login_entry = index.entries[2]

    return RelevantFileRetrievalResult(
        question=QUESTION,
        total_files=2,
        files=(
            RelevantFile(
                filename="app/auth.py",
                relevance_score=1,
                matched_entities=(auth_entry,),
            ),
            RelevantFile(
                filename="app/login.py",
                relevance_score=1,
                matched_entities=(login_entry,),
            ),
        ),
    )


@pytest.fixture
def service():
    return RelevantCodeRetrievalService()


@pytest.fixture
def empty_index():
    return CodeIndexResult(
        index_version=1,
        entries=(),
        total_entities=0,
        total_files=0,
        files=(),
        entity_counts={},
        by_file={},
    )


@pytest.fixture
def empty_relevant_files():
    return RelevantFileRetrievalResult(
        question=QUESTION,
        total_files=0,
        files=(),
    )


# ---------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------


def test_service_initialization():
    service = RelevantCodeRetrievalService()

    assert service is not None


# ---------------------------------------------------------
# Result model tests
# ---------------------------------------------------------


def test_result_creation(index):
    result = RelevantCodeRetrievalResult(
        question=QUESTION,
        total_code_entities=1,
        code_entities=(index.entries[0],),
    )

    assert result.question == QUESTION
    assert result.total_code_entities == 1
    assert len(result.code_entities) == 1


def test_result_accepts_empty_entities():
    result = RelevantCodeRetrievalResult(
        question=QUESTION,
        total_code_entities=0,
        code_entities=(),
    )

    assert result.total_code_entities == 0
    assert result.code_entities == ()


def test_result_rejects_empty_question(index):
    with pytest.raises(RelevantCodeRetrievalError):
        RelevantCodeRetrievalResult(
            question="",
            total_code_entities=1,
            code_entities=(index.entries[0],),
        )


def test_result_rejects_invalid_total(index):
    with pytest.raises(RelevantCodeRetrievalError):
        RelevantCodeRetrievalResult(
            question=QUESTION,
            total_code_entities=-1,
            code_entities=(index.entries[0],),
        )


def test_result_rejects_total_mismatch(index):
    with pytest.raises(RelevantCodeRetrievalError):
        RelevantCodeRetrievalResult(
            question=QUESTION,
            total_code_entities=2,
            code_entities=(index.entries[0],),
        )


def test_result_rejects_non_tuple_entities(index):
    with pytest.raises(RelevantCodeRetrievalError):
        RelevantCodeRetrievalResult(
            question=QUESTION,
            total_code_entities=1,
            code_entities=[index.entries[0]],
        )


def test_result_rejects_invalid_entity():
    with pytest.raises(RelevantCodeRetrievalError):
        RelevantCodeRetrievalResult(
            question=QUESTION,
            total_code_entities=1,
            code_entities=("invalid",),
        )


# ---------------------------------------------------------
# Successful retrieval tests
# ---------------------------------------------------------


def test_retrieve_returns_expected_result(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    assert isinstance(result, RelevantCodeRetrievalResult)


def test_retrieve_preserves_question(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    assert result.question == QUESTION


def test_retrieve_returns_entities_from_relevant_files(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    filenames = {
        entry.filename
        for entry in result.code_entities
    }

    assert filenames == {
        "app/auth.py",
        "app/login.py",
    }


def test_retrieve_excludes_irrelevant_files(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    filenames = {
        entry.filename
        for entry in result.code_entities
    }

    assert "app/payment.py" not in filenames


def test_retrieve_preserves_original_index_entries(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    assert all(
        entry in index.entries
        for entry in result.code_entities
    )


def test_retrieve_returns_all_entities_in_relevant_files(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    assert len(result.code_entities) == 3


def test_retrieve_reports_correct_total(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    assert result.total_code_entities == len(result.code_entities)


def test_retrieve_orders_entities_deterministically(
    service,
    index,
    relevant_files,
):
    first = service.retrieve(index, relevant_files)
    second = service.retrieve(index, relevant_files)

    assert first.code_entities == second.code_entities


def test_retrieve_orders_by_filename_and_line(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(index, relevant_files)

    ordering = [
        (entry.filename, entry.line)
        for entry in result.code_entities
    ]

    assert ordering == sorted(ordering)


# ---------------------------------------------------------
# Limit tests
# ---------------------------------------------------------


def test_retrieve_respects_limit(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(
        index,
        relevant_files,
        limit=2,
    )

    assert len(result.code_entities) == 2


def test_retrieve_accepts_large_limit(
    service,
    index,
    relevant_files,
):
    result = service.retrieve(
        index,
        relevant_files,
        limit=100,
    )

    assert len(result.code_entities) == 3


def test_retrieve_rejects_zero_limit(
    service,
    index,
    relevant_files,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            index,
            relevant_files,
            limit=0,
        )


def test_retrieve_rejects_negative_limit(
    service,
    index,
    relevant_files,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            index,
            relevant_files,
            limit=-1,
        )


def test_retrieve_rejects_non_integer_limit(
    service,
    index,
    relevant_files,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            index,
            relevant_files,
            limit="5",
        )


def test_retrieve_rejects_boolean_limit(
    service,
    index,
    relevant_files,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            index,
            relevant_files,
            limit=True,
        )


# ---------------------------------------------------------
# Validation tests
# ---------------------------------------------------------


def test_retrieve_rejects_invalid_index(
    service,
    relevant_files,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            "invalid",
            relevant_files,
        )


def test_retrieve_rejects_none_index(
    service,
    relevant_files,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            None,
            relevant_files,
        )


def test_retrieve_rejects_invalid_relevant_files(
    service,
    index,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            index,
            "invalid",
        )


def test_retrieve_rejects_none_relevant_files(
    service,
    index,
):
    with pytest.raises(RelevantCodeRetrievalError):
        service.retrieve(
            index,
            None,
        )


# ---------------------------------------------------------
# Empty result tests
# ---------------------------------------------------------


def test_retrieve_from_empty_index(
    service,
    empty_index,
    relevant_files,
):
    result = service.retrieve(
        empty_index,
        relevant_files,
    )

    assert result.total_code_entities == 0
    assert result.code_entities == ()


def test_retrieve_with_no_relevant_files(
    service,
    index,
    empty_relevant_files,
):
    result = service.retrieve(
        index,
        empty_relevant_files,
    )

    assert result.total_code_entities == 0
    assert result.code_entities == ()


def test_retrieve_returns_empty_result_when_files_do_not_match(
    service,
    index,
):
    unrelated_file = RelevantFile(
        filename="app/unknown.py",
        relevance_score=1,
        matched_entities=(
            create_entry(
                "external-1",
                "unknown_function",
                "app/unknown.py",
            ),
        ),
    )

    files_result = RelevantFileRetrievalResult(
        question=QUESTION,
        total_files=1,
        files=(unrelated_file,),
    )

    result = service.retrieve(index, files_result)

    assert result.total_code_entities == 0
    assert result.code_entities == ()
