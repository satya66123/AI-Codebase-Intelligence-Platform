
import json

import pytest

from app.application.intelligence_memory_models import (
    IntelligenceMemory,
    MemoryType,
)
from app.application.intelligence_memory_storage import (
    IntelligenceMemoryStorage,
    IntelligenceMemoryStorageError,
)


@pytest.fixture
def storage(tmp_path):
    return IntelligenceMemoryStorage(tmp_path / "memory")


@pytest.fixture
def memory():
    return IntelligenceMemory(
        memory_id="memory-001",
        repository_id="repository-001",
        memory_type=MemoryType.CODE_ENTITY,
        content="Employee class represents employee records.",
        source_files=["models/employee.py"],
        related_entity_ids=["entity-001"],
        metadata={"language": "python"},
    )


def test_save_memory(storage, memory):
    result = storage.save(memory)

    assert result.memory_id == memory.memory_id


def test_saved_memory_exists_as_json(storage, memory):
    storage.save(memory)

    files = list(storage.storage_dir.rglob("*.json"))

    assert len(files) == 1


def test_saved_memory_contains_valid_json(storage, memory):
    storage.save(memory)

    files = list(storage.storage_dir.rglob("*.json"))

    with files[0].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["memory_id"] == memory.memory_id
    assert data["memory_type"] == "code_entity"


def test_load_saved_memory(storage, memory):
    storage.save(memory)

    result = storage.load(
        memory.repository_id,
        memory.memory_id,
    )

    assert result is not None
    assert result.memory_id == memory.memory_id
    assert result.content == memory.content


def test_load_missing_memory_returns_none(storage):
    result = storage.load("repository-001", "missing-memory")

    assert result is None


def test_save_duplicate_memory_rejected(storage, memory):
    storage.save(memory)

    with pytest.raises(IntelligenceMemoryStorageError):
        storage.save(memory)


def test_update_existing_memory(storage, memory):
    storage.save(memory)

    updated = IntelligenceMemory(
        memory_id=memory.memory_id,
        repository_id=memory.repository_id,
        memory_type=MemoryType.CODE_ENTITY,
        content="Updated employee class information.",
        metadata={"language": "python", "updated": True},
    )

    result = storage.update(updated)

    assert result.content == "Updated employee class information."
    assert result.metadata["updated"] is True


def test_update_preserves_created_timestamp(storage, memory):
    storage.save(memory)

    updated = IntelligenceMemory(
        memory_id=memory.memory_id,
        repository_id=memory.repository_id,
        memory_type=MemoryType.CODE_ENTITY,
        content="Updated content.",
    )

    result = storage.update(updated)

    assert result.created_at == memory.created_at


def test_update_preserves_updated_timestamp_from_input(storage, memory):
    storage.save(memory)

    updated = IntelligenceMemory(
        memory_id=memory.memory_id,
        repository_id=memory.repository_id,
        memory_type=MemoryType.CODE_ENTITY,
        content="Updated content.",
        updated_at="2026-11-25T12:00:00+00:00",
    )

    result = storage.update(updated)

    assert result.updated_at == "2026-11-25T12:00:00+00:00"


def test_update_missing_memory_rejected(storage, memory):
    with pytest.raises(IntelligenceMemoryStorageError):
        storage.update(memory)


def test_load_returns_updated_memory(storage, memory):
    storage.save(memory)

    updated = IntelligenceMemory(
        memory_id=memory.memory_id,
        repository_id=memory.repository_id,
        memory_type=MemoryType.CODE_ENTITY,
        content="New content.",
    )

    storage.update(updated)

    result = storage.load(
        memory.repository_id,
        memory.memory_id,
    )

    assert result.content == "New content."


def test_delete_existing_memory(storage, memory):
    storage.save(memory)

    assert storage.delete(
        memory.repository_id,
        memory.memory_id,
    ) is True


def test_delete_missing_memory_returns_false(storage):
    assert storage.delete("repository-001", "missing") is False


def test_deleted_memory_cannot_be_loaded(storage, memory):
    storage.save(memory)
    storage.delete(memory.repository_id, memory.memory_id)

    result = storage.load(
        memory.repository_id,
        memory.memory_id,
    )

    assert result is None


def test_list_memories_for_repository(storage, memory):
    second = IntelligenceMemory(
        memory_id="memory-002",
        repository_id=memory.repository_id,
        memory_type=MemoryType.FILE,
        content="Employee source file.",
    )

    storage.save(memory)
    storage.save(second)

    results = storage.list_memories(memory.repository_id)

    assert len(results) == 2
    assert {item.memory_id for item in results} == {
        "memory-001",
        "memory-002",
    }


def test_list_memories_for_empty_repository(storage):
    assert storage.list_memories("empty-repository") == ()


def test_memories_are_isolated_by_repository(storage, memory):
    other = IntelligenceMemory(
        memory_id="memory-001",
        repository_id="repository-002",
        memory_type=MemoryType.REPOSITORY,
        content="Another repository.",
    )

    storage.save(memory)
    storage.save(other)

    results = storage.list_memories("repository-002")

    assert len(results) == 1
    assert results[0].repository_id == "repository-002"


def test_count_memories(storage, memory):
    storage.save(memory)

    assert storage.count_memories(memory.repository_id) == 1


def test_count_memories_after_deletion(storage, memory):
    storage.save(memory)
    storage.delete(memory.repository_id, memory.memory_id)

    assert storage.count_memories(memory.repository_id) == 0


def test_invalid_repository_id_rejected(storage):
    with pytest.raises(IntelligenceMemoryStorageError):
        storage.list_memories(" ")


def test_invalid_memory_id_rejected(storage):
    with pytest.raises(IntelligenceMemoryStorageError):
        storage.load("repository-001", " ")


def test_invalid_memory_object_rejected(storage):
    with pytest.raises(IntelligenceMemoryStorageError):
        storage.save({"memory_id": "invalid"})


def test_corrupted_json_rejected(storage, memory):
    storage.save(memory)

    files = list(storage.storage_dir.rglob("*.json"))
    files[0].write_text("{invalid json", encoding="utf-8")

    with pytest.raises(IntelligenceMemoryStorageError):
        storage.load(memory.repository_id, memory.memory_id)


def test_invalid_json_structure_rejected(storage, memory):
    storage.save(memory)

    files = list(storage.storage_dir.rglob("*.json"))
    files[0].write_text(
        json.dumps({"invalid": "structure"}),
        encoding="utf-8",
    )

    with pytest.raises(IntelligenceMemoryStorageError):
        storage.load(memory.repository_id, memory.memory_id)
