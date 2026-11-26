
import pytest

from appy.application.code_entity_extractor import CodeEntity
from appy.application.code_indexing_service import (
    CodeIndexEntry,
    CodeIndexingError,
    CodeIndexingService,
    CodeIndexResult,
)


@pytest.fixture
def service():
    return CodeIndexingService()


@pytest.fixture
def sample_entities():
    return [
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
            docstring="Perform work",
        ),
        CodeEntity(
            name="calculate",
            entity_type="function",
            qualified_name="services.calculate",
            filename="services.py",
            line=2,
            end_line=4,
            parent="services",
            docstring=None,
        ),
    ]


def test_build_index_returns_result(service, sample_entities):
    result = service.build_index(sample_entities)

    assert isinstance(result, CodeIndexResult)


def test_build_index_creates_entries(service, sample_entities):
    result = service.build_index(sample_entities)

    assert len(result.entries) == 3
    assert all(
        isinstance(entry, CodeIndexEntry)
        for entry in result.entries
    )


def test_index_entity_metadata(service, sample_entities):
    result = service.build_index(sample_entities)

    entry = result.entries[0]

    assert entry.name == "Employee"
    assert entry.entity_type == "class"
    assert entry.qualified_name == "models.Employee"
    assert entry.filename == "models.py"
    assert entry.line == 1
    assert entry.end_line == 8
    assert entry.parent == "models"
    assert entry.docstring == "Employee model"


def test_normalize_entity_name(service, sample_entities):
    result = service.build_index(sample_entities)

    assert result.entries[0].normalized_name == "employee"


def test_create_search_text(service, sample_entities):
    result = service.build_index(sample_entities)

    entry = result.entries[0]

    assert "employee" in entry.search_text
    assert "class" in entry.search_text
    assert "models.employee" in entry.search_text
    assert "employee model" in entry.search_text


def test_generate_entity_ids(service, sample_entities):
    result = service.build_index(sample_entities)

    entity_ids = [
        entry.entity_id
        for entry in result.entries
    ]

    assert len(entity_ids) == len(set(entity_ids))


def test_count_total_entities(service, sample_entities):
    result = service.build_index(sample_entities)

    assert result.total_entities == 3


def test_count_total_files(service, sample_entities):
    result = service.build_index(sample_entities)

    assert result.total_files == 2


def test_group_entities_by_file(service, sample_entities):
    result = service.build_index(sample_entities)

    assert result.files == ("models.py", "services.py")
    assert len(result.by_file["models.py"]) == 2
    assert len(result.by_file["services.py"]) == 1


def test_count_entity_types(service, sample_entities):
    result = service.build_index(sample_entities)

    assert result.entity_counts == {
        "class": 1,
        "method": 1,
        "function": 1,
    }


def test_empty_entities(service):
    result = service.build_index([])

    assert result.entries == ()
    assert result.total_entities == 0
    assert result.total_files == 0
    assert result.files == ()
    assert result.entity_counts == {}
    assert result.by_file == {}


def test_index_version(service):
    result = service.build_index([])

    assert result.index_version == 1


def test_reject_none_input(service):
    with pytest.raises(
        CodeIndexingError,
        match="iterable of CodeEntity",
    ):
        service.build_index(None)


def test_reject_invalid_entity(service):
    with pytest.raises(
        CodeIndexingError,
        match="CodeEntity instance",
    ):
        service.build_index(["invalid"])


def test_reject_empty_entity_name(service):
    entity = CodeEntity(
        name="",
        entity_type="function",
        qualified_name="appy.run",
        filename="appy.py",
        line=1,
        end_line=2,
        parent="appy",
        docstring=None,
    )

    with pytest.raises(
        CodeIndexingError,
        match="name must be a non-empty string",
    ):
        service.build_index([entity])


def test_reject_invalid_line_number(service):
    entity = CodeEntity(
        name="run",
        entity_type="function",
        qualified_name="appy.run",
        filename="appy.py",
        line=0,
        end_line=2,
        parent="appy",
        docstring=None,
    )

    with pytest.raises(
        CodeIndexingError,
        match="positive integer",
    ):
        service.build_index([entity])


def test_reject_invalid_end_line(service):
    entity = CodeEntity(
        name="run",
        entity_type="function",
        qualified_name="appy.run",
        filename="appy.py",
        line=5,
        end_line=3,
        parent="appy",
        docstring=None,
    )

    with pytest.raises(
        CodeIndexingError,
        match="end_line",
    ):
        service.build_index([entity])
