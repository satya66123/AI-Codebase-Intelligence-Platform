
from unittest.mock import Mock

import pytest

from app.application.repository_retrieval_service import (
    RepositoryRetrievalError,
    RepositoryRetrievalResult,
    RepositoryRetrievalService,
)
from app.application.question_analysis_agent import (
    QuestionAnalysisResult,
)
from app.application.intent_detection_service import QueryIntent
from app.application.context_memory_retrieval_service import (
    ContextMemoryRetrievalError,
)


@pytest.fixture
def analysis_result():
    return QuestionAnalysisResult(
        question="Explain the project architecture.",
        intent=QueryIntent.ARCHITECTURE,
        confidence=0.9,
        matched_terms=("architecture",),
    )


@pytest.fixture
def memory_service():
    service = Mock()
    service.retrieve.return_value = Mock(name="retrieval_result")
    return service


@pytest.fixture
def repository_service(memory_service):
    return RepositoryRetrievalService(memory_service)


def test_retrieve_returns_repository_retrieval_result(
    repository_service,
    analysis_result,
):
    result = repository_service.retrieve(
        repository_id="repo-001",
        analysis_result=analysis_result,
    )

    assert isinstance(result, RepositoryRetrievalResult)
    assert result.repository_id == "repo-001"
    assert result.question == analysis_result.question
    assert result.intent == QueryIntent.ARCHITECTURE


def test_retrieve_passes_question_to_memory_service(
    repository_service,
    memory_service,
    analysis_result,
):
    repository_service.retrieve(
        repository_id="repo-001",
        analysis_result=analysis_result,
    )

    memory_service.retrieve.assert_called_once_with(
        repository_id="repo-001",
        query="Explain the project architecture.",
        limit=10,
    )


def test_retrieve_passes_custom_limit(
    repository_service,
    memory_service,
    analysis_result,
):
    repository_service.retrieve(
        repository_id="repo-001",
        analysis_result=analysis_result,
        limit=5,
    )

    memory_service.retrieve.assert_called_once_with(
        repository_id="repo-001",
        query=analysis_result.question,
        limit=5,
    )


def test_retrieve_preserves_retrieval_data(
    repository_service,
    memory_service,
    analysis_result,
):
    expected_data = memory_service.retrieve.return_value

    result = repository_service.retrieve(
        repository_id="repo-001",
        analysis_result=analysis_result,
    )

    assert result.retrieval_data is expected_data


@pytest.mark.parametrize(
    "repository_id",
    ["", " ", None, 123, [], {}],
)
def test_retrieve_rejects_invalid_repository_id(
    repository_service,
    analysis_result,
    repository_id,
):
    with pytest.raises(RepositoryRetrievalError):
        repository_service.retrieve(
            repository_id=repository_id,
            analysis_result=analysis_result,
        )


@pytest.mark.parametrize(
    "analysis_result",
    [None, "invalid", 123, {}],
)
def test_retrieve_rejects_invalid_analysis_result(
    repository_service,
    analysis_result,
):
    with pytest.raises(RepositoryRetrievalError):
        repository_service.retrieve(
            repository_id="repo-001",
            analysis_result=analysis_result,
        )


@pytest.mark.parametrize(
    "limit",
    [0, -1, True, 1.5, "10", None],
)
def test_retrieve_rejects_invalid_limit(
    repository_service,
    analysis_result,
    limit,
):
    with pytest.raises(RepositoryRetrievalError):
        repository_service.retrieve(
            repository_id="repo-001",
            analysis_result=analysis_result,
            limit=limit,
        )


def test_constructor_rejects_invalid_memory_service():
    with pytest.raises(RepositoryRetrievalError):
        RepositoryRetrievalService(memory_retrieval_service=None)


def test_constructor_rejects_service_without_retrieve_method():
    with pytest.raises(RepositoryRetrievalError):
        RepositoryRetrievalService(
            memory_retrieval_service=object()
        )


def test_retrieve_wraps_memory_retrieval_error(
    repository_service,
    memory_service,
    analysis_result,
):
    memory_service.retrieve.side_effect = ContextMemoryRetrievalError(
        "Memory unavailable."
    )

    with pytest.raises(
        RepositoryRetrievalError,
        match="Repository memory retrieval failed",
    ):
        repository_service.retrieve(
            repository_id="repo-001",
            analysis_result=analysis_result,
        )


def test_retrieve_wraps_unexpected_errors(
    repository_service,
    memory_service,
    analysis_result,
):
    memory_service.retrieve.side_effect = RuntimeError(
        "Unexpected failure."
    )

    with pytest.raises(
        RepositoryRetrievalError,
        match="Unexpected repository retrieval error",
    ):
        repository_service.retrieve(
            repository_id="repo-001",
            analysis_result=analysis_result,
        )


def test_result_rejects_empty_repository_id():
    with pytest.raises(RepositoryRetrievalError):
        RepositoryRetrievalResult(
            repository_id=" ",
            question="Explain architecture.",
            intent=QueryIntent.ARCHITECTURE,
            retrieval_data=object(),
        )


def test_result_rejects_empty_question():
    with pytest.raises(RepositoryRetrievalError):
        RepositoryRetrievalResult(
            repository_id="repo-001",
            question=" ",
            intent=QueryIntent.ARCHITECTURE,
            retrieval_data=object(),
        )


def test_result_rejects_invalid_intent():
    with pytest.raises(RepositoryRetrievalError):
        RepositoryRetrievalResult(
            repository_id="repo-001",
            question="Explain architecture.",
            intent="invalid",
            retrieval_data=object(),
        )


def test_result_rejects_none_retrieval_data():
    with pytest.raises(RepositoryRetrievalError):
        RepositoryRetrievalResult(
            repository_id="repo-001",
            question="Explain architecture.",
            intent=QueryIntent.ARCHITECTURE,
            retrieval_data=None,
        )


def test_result_is_immutable():
    result = RepositoryRetrievalResult(
        repository_id="repo-001",
        question="Explain architecture.",
        intent=QueryIntent.ARCHITECTURE,
        retrieval_data=object(),
    )

    with pytest.raises(AttributeError):
        result.repository_id = "repo-002"
