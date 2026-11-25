
import pytest

from app.application.code_entity_extractor import CodeEntity
from app.application.code_indexing_service import (
    CodeIndexingService,
)
from app.application.index_management_service import (
    IndexManagementError,
    IndexManagementService,
    ManagedIndex,
)


@pytest.fixture
def service():
    return IndexManagementService()


@pytest.fixture
def sample_index():
    entities = [
        CodeEntity(
            name="Employee",
            entity_type="class",
            qualified_name="models.Employee",
            filename="models.py",
            line=1,
            end_line=5,
            parent="models",
            docstring="Employee model",
        ),
        CodeEntity(
            name="calculate",
            entity_type="function",
            qualified_name="services.calculate",
            filename="services.py",
            line=1,
            end_line=3,
            parent="services",
            docstring=None,
        ),
    ]

    return CodeIndexingService().build_index(entities)


@pytest.fixture
def empty_index():
    return CodeIndexingService().build_index([])


def test_register_index(service, sample_index):
    result = service.register_index(
        "project-1",
        sample_index,
    )

    assert isinstance(result, ManagedIndex)
    assert result.index_id == "project-1"
    assert result.index == sample_index


def test_register_index_initial_version(service, sample_index):
    result = service.register_index(
        "project-1",
        sample_index,
    )

    assert result.version == 1


def test_register_index_metadata(service, sample_index):
    result = service.register_index(
        "project-1",
        sample_index,
    )

    assert result.total_entities == 2
    assert result.total_files == 2
    assert result.created_at
    assert result.updated_at


def test_get_registered_index(service, sample_index):
    service.register_index("project-1", sample_index)

    result = service.get_index("project-1")

    assert result is not None
    assert result.index == sample_index


def test_get_missing_index(service):
    assert service.get_index("missing") is None


def test_update_index(service, sample_index, empty_index):
    service.register_index("project-1", sample_index)

    result = service.update_index(
        "project-1",
        empty_index,
    )

    assert result.index == empty_index
    assert result.total_entities == 0


def test_update_increments_version(
    service,
    sample_index,
    empty_index,
):
    service.register_index("project-1", sample_index)

    result = service.update_index(
        "project-1",
        empty_index,
    )

    assert result.version == 2


def test_update_preserves_creation_timestamp(
    service,
    sample_index,
    empty_index,
):
    original = service.register_index(
        "project-1",
        sample_index,
    )

    updated = service.update_index(
        "project-1",
        empty_index,
    )

    assert updated.created_at == original.created_at


def test_update_changes_update_timestamp(
    service,
    sample_index,
    empty_index,
):
    original = service.register_index(
        "project-1",
        sample_index,
    )

    updated = service.update_index(
        "project-1",
        empty_index,
    )

    assert updated.updated_at


def test_reject_duplicate_index(service, sample_index):
    service.register_index("project-1", sample_index)

    with pytest.raises(
        IndexManagementError,
        match="already exists",
    ):
        service.register_index("project-1", sample_index)


def test_reject_update_missing_index(service, sample_index):
    with pytest.raises(
        IndexManagementError,
        match="does not exist",
    ):
        service.update_index("missing", sample_index)


def test_delete_existing_index(service, sample_index):
    service.register_index("project-1", sample_index)

    result = service.delete_index("project-1")

    assert result is True
    assert service.get_index("project-1") is None


def test_delete_missing_index(service):
    result = service.delete_index("missing")

    assert result is False


def test_list_indexes(service, sample_index, empty_index):
    service.register_index("project-1", sample_index)
    service.register_index("project-2", empty_index)

    result = service.list_indexes()

    assert len(result) == 2
    assert {item.index_id for item in result} == {
        "project-1",
        "project-2",
    }


def test_list_empty_indexes(service):
    assert service.list_indexes() == ()


def test_get_index_count(service, sample_index, empty_index):
    assert service.get_index_count() == 0

    service.register_index("project-1", sample_index)
    service.register_index("project-2", empty_index)

    assert service.get_index_count() == 2


def test_index_count_after_deletion(service, sample_index):
    service.register_index("project-1", sample_index)
    service.delete_index("project-1")

    assert service.get_index_count() == 0


def test_reject_empty_index_id(service, sample_index):
    with pytest.raises(
        IndexManagementError,
        match="Index ID",
    ):
        service.register_index("", sample_index)


def test_reject_invalid_index(service):
    with pytest.raises(
        IndexManagementError,
        match="CodeIndexResult",
    ):
        service.register_index("project-1", None)
