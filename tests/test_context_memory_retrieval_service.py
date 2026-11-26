
from datetime import datetime, timezone

import pytest

from appy.application.context_memory_retrieval_service import (
    ContextMemoryRetrievalError,
    ContextMemoryRetrievalResult,
    ContextMemoryRetrievalService,
)
from appy.application.intelligence_memory_models import (
    IntelligenceMemory,
    MemoryType,
)
from appy.application.intelligence_memory_storage import (
    IntelligenceMemoryStorage,
)


@pytest.fixture
def storage(tmp_path):
    return IntelligenceMemoryStorage(
        storage_dir=str(tmp_path / "memory")
    )


@pytest.fixture
def service(storage):
    return ContextMemoryRetrievalService(storage)


@pytest.fixture
def memories(storage):
    timestamp = datetime.now(timezone.utc).isoformat()

    items = [
        IntelligenceMemory(
            memory_id="memory-1",
            repository_id="repo-1",
            memory_type=MemoryType.CODE_ENTITY,
            content="UserService: Handles user authentication and registration",
            source_files=("appy/services/user_service.py",),
            related_entity_ids=("entity-user-service",),
            metadata={"language": "python"},
            created_at=timestamp,
            updated_at=timestamp,
        ),
        IntelligenceMemory(
            memory_id="memory-2",
            repository_id="repo-1",
            memory_type=MemoryType.DEPENDENCY,
            content="DatabaseService: Manages database connections",
            source_files=("appy/services/database_service.py",),
            related_entity_ids=("entity-database-service",),
            metadata={"language": "python"},
            created_at=timestamp,
            updated_at=timestamp,
        ),
        IntelligenceMemory(
            memory_id="memory-3",
            repository_id="repo-1",
            memory_type=MemoryType.FILE,
            content="user_service.py: Contains user service implementation",
            source_files=("appy/services/user_service.py",),
            related_entity_ids=("entity-user-service",),
            metadata={"language": "python"},
            created_at=timestamp,
            updated_at=timestamp,
        ),
        IntelligenceMemory(
            memory_id="memory-4",
            repository_id="repo-2",
            memory_type=MemoryType.CODE_ENTITY,
            content="PaymentService: Processes payment transactions",
            source_files=("appy/services/payment_service.py",),
            related_entity_ids=("entity-payment-service",),
            metadata={"language": "python"},
            created_at=timestamp,
            updated_at=timestamp,
        ),
    ]

    for memory in items:
        storage.save(memory)

    return items


# ---------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------

def test_service_initialization(storage):
    service = ContextMemoryRetrievalService(storage)

    assert service is not None


def test_service_rejects_invalid_storage():
    with pytest.raises(ContextMemoryRetrievalError):
        ContextMemoryRetrievalService(None)


# ---------------------------------------------------------
# Basic Retrieval Tests
# ---------------------------------------------------------

def test_retrieve_all_repository_memories(service, memories):
    result = service.retrieve("repo-1")

    assert result.total_matches == 3
    assert len(result.memories) == 3


def test_retrieve_does_not_include_other_repositories(
    service,
    memories,
):
    result = service.retrieve("repo-1")

    assert all(
        memory.repository_id == "repo-1"
        for memory in result.memories
    )


def test_retrieve_by_query(service, memories):
    result = service.retrieve(
        "repo-1",
        query="authentication",
    )

    assert result.total_matches == 1
    assert result.memories[0].memory_id == "memory-1"


def test_retrieve_query_is_case_insensitive(service, memories):
    result = service.retrieve(
        "repo-1",
        query="AUTHENTICATION",
    )

    assert result.total_matches == 1
    assert result.memories[0].memory_id == "memory-1"


def test_retrieve_returns_no_matches_for_unknown_query(
    service,
    memories,
):
    result = service.retrieve(
        "repo-1",
        query="unknownterm",
    )

    assert result.total_matches == 0
    assert result.memories == ()


# ---------------------------------------------------------
# Memory Type Retrieval Tests
# ---------------------------------------------------------

def test_retrieve_by_memory_type(service, memories):
    result = service.retrieve_by_type(
        "repo-1",
        MemoryType.CODE_ENTITY,
    )

    assert result.total_matches == 1
    assert result.memories[0].memory_id == "memory-1"


def test_retrieve_by_type_rejects_invalid_type(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve_by_type(
            "repo-1",
            "code_entity",
        )


def test_retrieve_with_multiple_memory_types(service, memories):
    result = service.retrieve(
        "repo-1",
        memory_types=(
            MemoryType.CODE_ENTITY,
            MemoryType.DEPENDENCY,
        ),
    )

    assert result.total_matches == 2


# ---------------------------------------------------------
# Source File and Entity Retrieval Tests
# ---------------------------------------------------------

def test_retrieve_by_source_file(service, memories):
    result = service.retrieve_by_source_file(
        "repo-1",
        "appy/services/user_service.py",
    )

    assert result.total_matches == 2


def test_retrieve_by_entity(service, memories):
    result = service.retrieve_by_entity(
        "repo-1",
        "entity-user-service",
    )

    assert result.total_matches == 2


def test_retrieve_with_combined_filters(service, memories):
    result = service.retrieve(
        "repo-1",
        memory_types=(MemoryType.CODE_ENTITY,),
        source_file="appy/services/user_service.py",
        related_entity_id="entity-user-service",
    )

    assert result.total_matches == 1
    assert result.memories[0].memory_id == "memory-1"


# ---------------------------------------------------------
# Limit and Validation Tests
# ---------------------------------------------------------

def test_retrieve_respects_limit(service, memories):
    result = service.retrieve(
        "repo-1",
        limit=2,
    )

    assert len(result.memories) == 2
    assert result.total_matches == 3


def test_retrieve_limit_must_be_positive(service, memories):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve(
            "repo-1",
            limit=0,
        )


def test_retrieve_rejects_invalid_repository_id(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve("")


def test_retrieve_rejects_invalid_query(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve(
            "repo-1",
            query=None,
        )


def test_retrieve_rejects_empty_source_file(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve(
            "repo-1",
            source_file=" ",
        )


def test_retrieve_rejects_empty_entity_id(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve(
            "repo-1",
            related_entity_id=" ",
        )


def test_retrieve_rejects_invalid_memory_types(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve(
            "repo-1",
            memory_types=("code_entity",),
        )


# ---------------------------------------------------------
# Result Model Tests
# ---------------------------------------------------------

def test_retrieve_result_is_immutable(service, memories):
    result = service.retrieve("repo-1")

    with pytest.raises(AttributeError):
        result.memories = ()


def test_retrieval_result_rejects_invalid_total_matches():
    with pytest.raises(ContextMemoryRetrievalError):
        ContextMemoryRetrievalResult(
            repository_id="repo-1",
            query="test",
            memories=(),
            total_matches=-1,
        )


def test_retrieval_result_rejects_non_memory_items():
    with pytest.raises(ContextMemoryRetrievalError):
        ContextMemoryRetrievalResult(
            repository_id="repo-1",
            query="test",
            memories=("invalid",),
            total_matches=1,
        )


def test_retrieval_result_rejects_more_memories_than_matches(
    memories,
):
    with pytest.raises(ContextMemoryRetrievalError):
        ContextMemoryRetrievalResult(
            repository_id="repo-1",
            query="test",
            memories=(memories[0],),
            total_matches=0,
        )


# ---------------------------------------------------------
# Empty Repository and Ranking Tests
# ---------------------------------------------------------

def test_empty_repository_returns_empty_result(service):
    result = service.retrieve("empty-repo")

    assert result.memories == ()
    assert result.total_matches == 0


def test_empty_query_returns_all_matching_memories(
    service,
    memories,
):
    result = service.retrieve(
        "repo-1",
        query="",
    )

    assert result.total_matches == 3


def test_memory_ranking_prefers_more_relevant_content(
    service,
    memories,
):
    result = service.retrieve(
        "repo-1",
        query="user authentication",
    )

    assert result.memories[0].memory_id == "memory-1"


# ---------------------------------------------------------
# Convenience Method Validation Tests
# ---------------------------------------------------------

def test_retrieve_by_source_file_rejects_empty_path(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve_by_source_file(
            "repo-1",
            "",
        )


def test_retrieve_by_entity_rejects_empty_id(service):
    with pytest.raises(ContextMemoryRetrievalError):
        service.retrieve_by_entity(
            "repo-1",
            "",
        )
