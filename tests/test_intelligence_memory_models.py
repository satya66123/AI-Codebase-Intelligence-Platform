
import json
from datetime import datetime, timezone

import pytest

from appy.application.intelligence_memory_models import (
    IntelligenceMemory,
    MemoryModelError,
    MemoryType,
)


@pytest.fixture
def memory():
    return IntelligenceMemory(
        memory_id="memory-001",
        repository_id="repository-001",
        memory_type=MemoryType.CODE_ENTITY,
        content="Employee class represents employee records.",
        source_files=["models/employee.py"],
        related_entity_ids=["entity-001"],
        metadata={"language": "python", "line": 10},
    )


def test_create_intelligence_memory(memory):
    assert memory.memory_id == "memory-001"
    assert memory.repository_id == "repository-001"
    assert memory.memory_type == MemoryType.CODE_ENTITY


def test_memory_content(memory):
    assert "Employee class" in memory.content


def test_memory_source_files(memory):
    assert memory.source_files == ("models/employee.py",)


def test_memory_related_entity_ids(memory):
    assert memory.related_entity_ids == ("entity-001",)


def test_memory_metadata(memory):
    assert memory.metadata["language"] == "python"
    assert memory.metadata["line"] == 10


def test_default_timestamps_are_timezone_aware(memory):
    created = datetime.fromisoformat(memory.created_at)
    updated = datetime.fromisoformat(memory.updated_at)

    assert created.tzinfo is not None
    assert updated.tzinfo is not None


def test_memory_type_values():
    assert MemoryType.REPOSITORY.value == "repository"
    assert MemoryType.DEPENDENCY.value == "dependency"
    assert MemoryType.ARCHITECTURE.value == "architecture"


def test_memory_id_must_not_be_empty():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id=" ",
            repository_id="repo-1",
            memory_type=MemoryType.REPOSITORY,
            content="Repository overview",
        )


def test_repository_id_must_not_be_empty():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id=" ",
            memory_type=MemoryType.REPOSITORY,
            content="Repository overview",
        )


def test_content_must_not_be_empty():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type=MemoryType.REPOSITORY,
            content=" ",
        )


def test_memory_type_must_be_valid():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type="unknown",
            content="Some knowledge",
        )


def test_source_files_must_be_a_collection():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type=MemoryType.FILE,
            content="File knowledge",
            source_files="models.py",
        )


def test_source_files_must_not_contain_empty_values():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type=MemoryType.FILE,
            content="File knowledge",
            source_files=["models.py", " "],
        )


def test_metadata_must_be_a_mapping():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type=MemoryType.REPOSITORY,
            content="Repository knowledge",
            metadata=["invalid"],
        )


def test_metadata_must_be_json_serializable():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type=MemoryType.REPOSITORY,
            content="Repository knowledge",
            metadata={"invalid": object()},
        )


def test_timestamps_must_include_timezone():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type=MemoryType.REPOSITORY,
            content="Repository knowledge",
            created_at="2026-11-25T10:00:00",
        )


def test_to_dict_returns_json_compatible_data(memory):
    result = memory.to_dict()

    assert result["memory_type"] == "code_entity"
    assert result["source_files"] == ["models/employee.py"]
    assert result["related_entity_ids"] == ["entity-001"]

    serialized = json.dumps(result)
    assert isinstance(serialized, str)


def test_from_dict_restores_memory(memory):
    restored = IntelligenceMemory.from_dict(memory.to_dict())

    assert restored.memory_id == memory.memory_id
    assert restored.repository_id == memory.repository_id
    assert restored.memory_type == memory.memory_type
    assert restored.content == memory.content
    assert restored.source_files == memory.source_files
    assert restored.related_entity_ids == memory.related_entity_ids
    assert dict(restored.metadata) == dict(memory.metadata)


def test_from_dict_rejects_missing_required_field():
    with pytest.raises(MemoryModelError):
        IntelligenceMemory.from_dict({
            "memory_id": "memory-1",
        })


def test_metadata_cannot_be_modified_through_model(memory):
    with pytest.raises(TypeError):
        memory.metadata["language"] = "java"


def test_input_metadata_is_copied():
    metadata = {"language": "python"}

    memory = IntelligenceMemory(
        memory_id="memory-1",
        repository_id="repo-1",
        memory_type=MemoryType.REPOSITORY,
        content="Repository knowledge",
        metadata=metadata,
    )

    metadata["language"] = "java"

    assert memory.metadata["language"] == "python"
