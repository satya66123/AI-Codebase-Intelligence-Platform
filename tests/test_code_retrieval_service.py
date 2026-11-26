
import pytest

from appy.application.code_entity_extractor import CodeEntity
from appy.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexingService,
)
from appy.application.code_retrieval_service import (
    CodeRetrievalError,
    CodeRetrievalResult,
    CodeRetrievalService,
)


@pytest.fixture
def service():
    return CodeRetrievalService()


@pytest.fixture
def code_index():
    entities = [
        CodeEntity(
            name="Employee",
            entity_type="class",
            qualified_name="models.Employee",
            filename="models.py",
            line=1,
            end_line=10,
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
            docstring="Perform work",
        ),
        CodeEntity(
            name="save",
            entity_type="method",
            qualified_name="models.Employee.save",
            filename="models.py",
            line=7,
            end_line=9,
            parent="models.Employee",
            docstring="Save employee",
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


def test_get_by_id_returns_entry(service, code_index):
    entity_id = code_index.entries[0].entity_id

    result = service.get_by_id(code_index, entity_id)

    assert isinstance(result, CodeIndexEntry)
    assert result.name == "Employee"


def test_get_by_id_returns_none_for_missing_entity(
    service,
    code_index,
):
    result = service.get_by_id(code_index, "missing-id")

    assert result is None


def test_get_by_qualified_name(service, code_index):
    result = service.get_by_qualified_name(
        code_index,
        "models.Employee.work",
    )

    assert len(result) == 1
    assert result[0].name == "work"


def test_qualified_name_lookup_is_case_insensitive(
    service,
    code_index,
):
    result = service.get_by_qualified_name(
        code_index,
        "MODELS.EMPLOYEE.WORK",
    )

    assert len(result) == 1


def test_get_by_file_returns_result(service, code_index):
    result = service.get_by_file(code_index, "models.py")

    assert isinstance(result, CodeRetrievalResult)
    assert result.query_type == "file"
    assert result.total_results == 3


def test_get_by_file_is_case_insensitive(service, code_index):
    result = service.get_by_file(code_index, "MODELS.PY")

    assert result.total_results == 3


def test_get_by_file_normalizes_path_separators(
    service,
    code_index,
):
    result = service.get_by_file(code_index, "models.py")

    assert result.total_results == 3


def test_get_by_parent(service, code_index):
    result = service.get_by_parent(
        code_index,
        "models.Employee",
    )

    assert result.total_results == 2
    assert {entry.name for entry in result.entries} == {
        "work",
        "save",
    }


def test_parent_lookup_is_case_insensitive(
    service,
    code_index,
):
    result = service.get_by_parent(
        code_index,
        "MODELS.EMPLOYEE",
    )

    assert result.total_results == 2


def test_get_by_line_range(service, code_index):
    result = service.get_by_line_range(
        code_index,
        "models.py",
        3,
        5,
    )

    assert result.query_type == "line_range"
    assert result.total_results == 2
    assert {entry.name for entry in result.entries} == {
        "Employee",
        "work",
    }


def test_line_range_finds_overlapping_entities(
    service,
    code_index,
):
    result = service.get_by_line_range(
        code_index,
        "models.py",
        4,
        4,
    )

    assert result.total_results == 2


def test_line_range_returns_empty_for_other_file(
    service,
    code_index,
):
    result = service.get_by_line_range(
        code_index,
        "unknown.py",
        1,
        10,
    )

    assert result.entries == ()
    assert result.total_results == 0


def test_empty_index_retrieval(service):
    empty_index = CodeIndexingService().build_index([])

    result = service.get_by_file(empty_index, "appy.py")

    assert result.entries == ()
    assert result.total_results == 0


def test_reject_invalid_index(service):
    with pytest.raises(
        CodeRetrievalError,
        match="CodeIndexResult",
    ):
        service.get_by_file(None, "models.py")


def test_reject_empty_entity_id(service, code_index):
    with pytest.raises(
        CodeRetrievalError,
        match="Entity ID",
    ):
        service.get_by_id(code_index, "")


def test_reject_empty_qualified_name(service, code_index):
    with pytest.raises(
        CodeRetrievalError,
        match="Qualified name",
    ):
        service.get_by_qualified_name(code_index, " ")


def test_reject_empty_filename(service, code_index):
    with pytest.raises(
        CodeRetrievalError,
        match="Filename",
    ):
        service.get_by_file(code_index, "")


def test_reject_invalid_start_line(service, code_index):
    with pytest.raises(
        CodeRetrievalError,
        match="Start line",
    ):
        service.get_by_line_range(
            code_index,
            "models.py",
            0,
            5,
        )


def test_reject_invalid_end_line(service, code_index):
    with pytest.raises(
        CodeRetrievalError,
        match="End line",
    ):
        service.get_by_line_range(
            code_index,
            "models.py",
            5,
            3,
        )


def test_reject_boolean_line_number(service, code_index):
    with pytest.raises(
        CodeRetrievalError,
        match="Start line",
    ):
        service.get_by_line_range(
            code_index,
            "models.py",
            True,
            5,
        )
