
import pytest

from appy.application.code_entity_extractor import CodeEntity
from appy.application.code_indexing_service import CodeIndexingService
from appy.application.code_search_service import (
    CodeSearchError,
    CodeSearchService,
)


@pytest.fixture
def search_service():
    return CodeSearchService()


@pytest.fixture
def code_index():
    entities = [
        CodeEntity(
            name="Employee",
            entity_type="class",
            qualified_name="models.Employee",
            filename="models.py",
            line=1,
            end_line=8,
            parent="models",
            docstring="Employee model",
        ),
        CodeEntity(
            name="work",
            entity_type="method",
            qualified_name="models.Employee.work",
            filename="models.py",
            line=3,
            end_line=5,
            parent="models.Employee",
            docstring="Perform employee work",
        ),
        CodeEntity(
            name="calculate",
            entity_type="function",
            qualified_name="services.calculate",
            filename="services.py",
            line=2,
            end_line=4,
            parent="services",
            docstring="Calculate a result",
        ),
    ]

    return CodeIndexingService().build_index(entities)


def test_search_returns_matching_entries(search_service, code_index):
    results = search_service.search(code_index, "Employee")

    assert len(results) == 2


def test_search_is_case_insensitive(search_service, code_index):
    results = search_service.search(code_index, "EMPLOYEE")

    assert len(results) == 2


def test_search_supports_partial_matching(search_service, code_index):
    results = search_service.search(code_index, "calcul")

    assert len(results) == 1
    assert results[0].name == "calculate"


def test_search_by_qualified_name(search_service, code_index):
    results = search_service.search(
        code_index,
        "models.Employee.work",
    )

    assert len(results) == 1
    assert results[0].name == "work"


def test_search_by_filename(search_service, code_index):
    results = search_service.search(code_index, "services.py")

    assert len(results) == 1
    assert results[0].filename == "services.py"


def test_search_by_docstring(search_service, code_index):
    results = search_service.search(code_index, "perform employee work")

    assert len(results) == 1
    assert results[0].name == "work"


def test_filter_by_entity_type(search_service, code_index):
    results = search_service.search(
        code_index,
        "Employee",
        entity_type="method",
    )

    assert len(results) == 1
    assert results[0].entity_type == "method"


def test_entity_type_filter_is_case_insensitive(
    search_service,
    code_index,
):
    results = search_service.search(
        code_index,
        "calculate",
        entity_type="FUNCTION",
    )

    assert len(results) == 1


def test_exact_match_by_name(search_service, code_index):
    results = search_service.search(
        code_index,
        "Employee",
        exact_match=True,
    )

    assert len(results) == 1
    assert results[0].name == "Employee"


def test_exact_match_by_qualified_name(search_service, code_index):
    results = search_service.search(
        code_index,
        "models.Employee",
        exact_match=True,
    )

    assert len(results) == 1


def test_exact_match_does_not_return_partial_results(
    search_service,
    code_index,
):
    results = search_service.search(
        code_index,
        "Employ",
        exact_match=True,
    )

    assert results == ()


def test_search_no_results(search_service, code_index):
    results = search_service.search(
        code_index,
        "nonexistent",
    )

    assert results == ()


def test_search_empty_index(search_service):
    empty_index = CodeIndexingService().build_index([])

    results = search_service.search(empty_index, "anything")

    assert results == ()


def test_reject_invalid_index(search_service):
    with pytest.raises(
        CodeSearchError,
        match="CodeIndexResult",
    ):
        search_service.search(None, "Employee")


def test_reject_empty_query(search_service, code_index):
    with pytest.raises(
        CodeSearchError,
        match="non-empty string",
    ):
        search_service.search(code_index, "")


def test_reject_invalid_entity_type(search_service, code_index):
    with pytest.raises(
        CodeSearchError,
        match="Entity type",
    ):
        search_service.search(
            code_index,
            "Employee",
            entity_type=" ",
        )


def test_reject_invalid_exact_match(search_service, code_index):
    with pytest.raises(
        CodeSearchError,
        match="exact_match",
    ):
        search_service.search(
            code_index,
            "Employee",
            exact_match="yes",
        )
