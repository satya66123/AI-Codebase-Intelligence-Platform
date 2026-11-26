
"""Tests for IntelligenceMemoryManagementService."""

from datetime import datetime, timedelta, timezone

import pytest

from appy.application.intelligence_memory_models import (
    IntelligenceMemory,
    MemoryType,
    MemoryModelError,
)
from appy.application.intelligence_memory_storage import (
    IntelligenceMemoryStorage,
)
from appy.application.intelligence_memory_management_service import (
    IntelligenceMemoryManagementError,
    IntelligenceMemoryManagementService,
    MemoryAction,
    MemoryManagementResult,
    RepositoryMemorySummary,
)


@pytest.fixture
def storage(tmp_path):
    return IntelligenceMemoryStorage(
        storage_dir=tmp_path / "intelligence_memory"
    )


@pytest.fixture
def service(storage):
    return IntelligenceMemoryManagementService(storage)


@pytest.fixture
def memory():
    timestamp = datetime.now(timezone.utc).isoformat()

    return IntelligenceMemory(
        memory_id="memory-1",
        repository_id="repo-1",
        memory_type=MemoryType.CODE_ENTITY,
        content="UserService handles authentication and registration.",
        source_files=("appy/services/user_service.py",),
        related_entity_ids=("entity-user-service",),
        metadata={"language": "python"},
        created_at=timestamp,
        updated_at=timestamp,
    )


def make_memory(
    memory_id="memory-1",
    repository_id="repo-1",
    memory_type=MemoryType.CODE_ENTITY,
    content="UserService handles authentication.",
    created_at=None,
    updated_at=None,
):
    now = datetime.now(timezone.utc)

    return IntelligenceMemory(
        memory_id=memory_id,
        repository_id=repository_id,
        memory_type=memory_type,
        content=content,
        source_files=("appy/services/user_service.py",),
        related_entity_ids=("entity-user-service",),
        metadata={"language": "python"},
        created_at=created_at or now.isoformat(),
        updated_at=updated_at or now.isoformat(),
    )


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def test_service_initialization(storage):
    service = IntelligenceMemoryManagementService(storage)

    assert service is not None
    assert service._storage is storage


def test_service_rejects_invalid_storage():
    with pytest.raises(IntelligenceMemoryManagementError):
        IntelligenceMemoryManagementService(None)


# ---------------------------------------------------------------------
# Result model validation
# ---------------------------------------------------------------------

def test_memory_management_result():
    result = MemoryManagementResult(
        repository_id="repo-1",
        action=MemoryAction.CREATED,
        affected_count=1,
    )

    assert result.repository_id == "repo-1"
    assert result.action == MemoryAction.CREATED
    assert result.affected_count == 1


@pytest.mark.parametrize(
    "repository_id",
    ["", " ", None],
)
def test_memory_management_result_rejects_invalid_repository_id(
    repository_id,
):
    with pytest.raises(ValueError):
        MemoryManagementResult(
            repository_id=repository_id,
            action=MemoryAction.CREATED,
            affected_count=1,
        )


def test_memory_management_result_rejects_invalid_action():
    with pytest.raises(ValueError):
        MemoryManagementResult(
            repository_id="repo-1",
            action="created",
            affected_count=1,
        )


@pytest.mark.parametrize(
    "count",
    [-1, 1.5, True],
)
def test_memory_management_result_rejects_invalid_count(count):
    with pytest.raises(ValueError):
        MemoryManagementResult(
            repository_id="repo-1",
            action=MemoryAction.CREATED,
            affected_count=count,
        )


# ---------------------------------------------------------------------
# Save memory
# ---------------------------------------------------------------------

def test_save_memory(service, storage, memory):
    result = service.save_memory(memory)

    assert result.action == MemoryAction.CREATED
    assert result.affected_count == 1

    saved = storage.load("repo-1", "memory-1")
    assert saved == memory


def test_save_memory_rejects_invalid_memory(service):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.save_memory(None)


def test_save_memory_rejects_duplicate_memory(service, memory):
    service.save_memory(memory)

    with pytest.raises(IntelligenceMemoryManagementError):
        service.save_memory(memory)


# ---------------------------------------------------------------------
# Update memory
# ---------------------------------------------------------------------

def test_update_memory(service, storage, memory):
    service.save_memory(memory)

    original_created_at = memory.created_at

    updated_time = (
        datetime.now(timezone.utc) + timedelta(minutes=1)
    ).isoformat()

    updated = make_memory(
        memory_id=memory.memory_id,
        repository_id=memory.repository_id,
        content=(
            "UserService now supports authentication "
            "and authorization."
        ),
        created_at=updated_time,
        updated_at=updated_time,
    )

    result = service.update_memory(updated)

    assert result.action == MemoryAction.UPDATED
    assert result.affected_count == 1

    stored = storage.load("repo-1", "memory-1")

    assert stored.content == (
        "UserService now supports authentication "
        "and authorization."
    )
    assert stored.created_at == original_created_at
    assert stored.updated_at == updated_time


def test_update_memory_rejects_invalid_memory(service):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.update_memory(None)


def test_update_memory_rejects_missing_memory(service, memory):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.update_memory(memory)


# ---------------------------------------------------------------------
# Upsert memory
# ---------------------------------------------------------------------

def test_upsert_creates_new_memory(service, storage, memory):
    result = service.upsert_memory(memory)

    assert result.action == MemoryAction.CREATED
    assert result.affected_count == 1

    assert storage.load("repo-1", "memory-1") == memory


def test_upsert_updates_existing_memory(service, storage, memory):
    service.save_memory(memory)

    updated = make_memory(
        content="Updated UserService authentication implementation."
    )

    result = service.upsert_memory(updated)

    assert result.action == MemoryAction.UPDATED

    stored = storage.load("repo-1", "memory-1")

    assert stored.content == (
        "Updated UserService authentication implementation."
    )


def test_upsert_rejects_invalid_memory(service):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.upsert_memory(None)


# ---------------------------------------------------------------------
# Delete memory
# ---------------------------------------------------------------------

def test_delete_memory(service, storage, memory):
    service.save_memory(memory)

    result = service.delete_memory("repo-1", "memory-1")

    assert result.action == MemoryAction.DELETED
    assert result.affected_count == 1
    assert storage.load("repo-1", "memory-1") is None


def test_delete_missing_memory_returns_zero(service):
    result = service.delete_memory("repo-1", "missing-memory")

    assert result.action == MemoryAction.DELETED
    assert result.affected_count == 0


@pytest.mark.parametrize(
    "repository_id",
    ["", " ", None],
)
def test_delete_memory_rejects_invalid_repository_id(
    service,
    repository_id,
):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.delete_memory(repository_id, "memory-1")


@pytest.mark.parametrize(
    "memory_id",
    ["", " ", None],
)
def test_delete_memory_rejects_invalid_memory_id(
    service,
    memory_id,
):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.delete_memory("repo-1", memory_id)


# ---------------------------------------------------------------------
# Delete memories by type
# ---------------------------------------------------------------------

def test_delete_memories_by_type(service, storage):
    service.save_memory(
        make_memory(
            memory_id="entity-1",
            memory_type=MemoryType.CODE_ENTITY,
        )
    )

    service.save_memory(
        make_memory(
            memory_id="entity-2",
            memory_type=MemoryType.CODE_ENTITY,
        )
    )

    service.save_memory(
        make_memory(
            memory_id="file-1",
            memory_type=MemoryType.FILE,
        )
    )

    result = service.delete_memories_by_type(
        "repo-1",
        MemoryType.CODE_ENTITY,
    )

    assert result.action == MemoryAction.DELETED_BY_TYPE
    assert result.affected_count == 2

    remaining = storage.list_memories("repo-1")

    assert len(remaining) == 1
    assert remaining[0].memory_type == MemoryType.FILE


def test_delete_memories_by_type_returns_zero_when_no_matches(service):
    result = service.delete_memories_by_type(
        "repo-1",
        MemoryType.DEPENDENCY,
    )

    assert result.action == MemoryAction.DELETED_BY_TYPE
    assert result.affected_count == 0


def test_delete_memories_by_type_rejects_invalid_repository(service):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.delete_memories_by_type(
            "",
            MemoryType.CODE_ENTITY,
        )


def test_delete_memories_by_type_rejects_invalid_type(service):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.delete_memories_by_type(
            "repo-1",
            "code_entity",
        )


# ---------------------------------------------------------------------
# Repository memory summary
# ---------------------------------------------------------------------

def test_get_repository_summary_for_empty_repository(service):
    summary = service.get_repository_summary("repo-1")

    assert isinstance(summary, RepositoryMemorySummary)
    assert summary.repository_id == "repo-1"
    assert summary.total_memories == 0

    assert all(
        count == 0
        for count in summary.memories_by_type.values()
    )


def test_get_repository_summary_counts_memory_types(service):
    service.save_memory(
        make_memory(
            memory_id="entity-1",
            memory_type=MemoryType.CODE_ENTITY,
        )
    )

    service.save_memory(
        make_memory(
            memory_id="entity-2",
            memory_type=MemoryType.CODE_ENTITY,
        )
    )

    service.save_memory(
        make_memory(
            memory_id="file-1",
            memory_type=MemoryType.FILE,
        )
    )

    service.save_memory(
        make_memory(
            memory_id="dependency-1",
            memory_type=MemoryType.DEPENDENCY,
        )
    )

    summary = service.get_repository_summary("repo-1")

    assert summary.total_memories == 4

    assert (
        summary.memories_by_type[MemoryType.CODE_ENTITY.value] == 2
    )

    assert summary.memories_by_type[MemoryType.FILE.value] == 1

    assert (
        summary.memories_by_type[MemoryType.DEPENDENCY.value] == 1
    )


def test_get_repository_summary_is_repository_specific(service):
    service.save_memory(
        make_memory(
            memory_id="repo-1-memory",
            repository_id="repo-1",
        )
    )

    service.save_memory(
        make_memory(
            memory_id="repo-2-memory",
            repository_id="repo-2",
        )
    )

    summary = service.get_repository_summary("repo-1")

    assert summary.total_memories == 1


def test_get_repository_summary_rejects_invalid_repository(service):
    with pytest.raises(IntelligenceMemoryManagementError):
        service.get_repository_summary("")


# ---------------------------------------------------------------------
# Memory model validation
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "repository_id",
    ["", " ", None],
)
def test_save_memory_rejects_invalid_memory_repository(
    service,
    repository_id,
):
    # The memory model validates repository_id during construction.
    with pytest.raises(MemoryModelError):
        make_memory(repository_id=repository_id)
