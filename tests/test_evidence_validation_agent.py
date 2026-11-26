
from dataclasses import FrozenInstanceError

import pytest

from appy.application.context_builder import ContextBuildResult
from appy.application.evidence_validation_agent import (
    EvidenceValidationAgent,
    EvidenceValidationError,
    EvidenceValidationResult,
)
from appy.application.intent_detection_service import QueryIntent
from appy.application.reasoning_response_model import ReasoningResponse


@pytest.fixture
def agent():
    return EvidenceValidationAgent()


@pytest.fixture
def context():
    context_text = "Repository architecture context"

    return ContextBuildResult(
        question="Explain the application architecture",
        intent="architecture",
        sections=(),
        context_text=context_text,
        source_files=(
            "appy/main.py",
            "appy/services/user.py",
        ),
        entity_ids=(
            "entity-1",
            "entity-2",
        ),
        character_count=len(context_text),
        max_characters=12000,
        truncated=False,
    )


@pytest.fixture
def response():
    return ReasoningResponse(
        question="Explain the application architecture",
        answer="The application uses a layered architecture.",
        intent=QueryIntent.ARCHITECTURE,
        source_files=(
            "appy/main.py",
            "appy/services/user.py",
        ),
        entity_ids=(
            "entity-1",
            "entity-2",
        ),
        provider_name="openai",
        model_name="gpt-4o",
        evidence_sufficient=True,
    )


def test_successful_validation_returns_valid_result(
    agent,
    response,
    context,
):
    result = agent.validate(response, context)

    assert isinstance(result, EvidenceValidationResult)
    assert result.is_valid is True
    assert result.evidence_sufficient is True
    assert result.issues == ()


def test_all_source_files_are_supported(
    agent,
    response,
    context,
):
    result = agent.validate(response, context)

    assert result.supported_source_files == (
        "appy/main.py",
        "appy/services/user.py",
    )
    assert result.unsupported_source_files == ()


def test_all_entity_ids_are_supported(
    agent,
    response,
    context,
):
    result = agent.validate(response, context)

    assert result.supported_entity_ids == (
        "entity-1",
        "entity-2",
    )
    assert result.unsupported_entity_ids == ()


def test_unsupported_source_file_is_detected(
    agent,
    response,
    context,
):
    modified_response = ReasoningResponse(
        question=response.question,
        answer=response.answer,
        intent=response.intent,
        source_files=(
            "appy/main.py",
            "appy/unknown.py",
        ),
        entity_ids=response.entity_ids,
        provider_name=response.provider_name,
        model_name=response.model_name,
        evidence_sufficient=True,
    )

    result = agent.validate(modified_response, context)

    assert result.is_valid is False
    assert result.supported_source_files == ("appy/main.py",)
    assert result.unsupported_source_files == ("appy/unknown.py",)
    assert len(result.issues) == 1


def test_unsupported_entity_id_is_detected(
    agent,
    response,
    context,
):
    modified_response = ReasoningResponse(
        question=response.question,
        answer=response.answer,
        intent=response.intent,
        source_files=response.source_files,
        entity_ids=(
            "entity-1",
            "unknown-entity",
        ),
        provider_name=response.provider_name,
        model_name=response.model_name,
        evidence_sufficient=True,
    )

    result = agent.validate(modified_response, context)

    assert result.is_valid is False
    assert result.supported_entity_ids == ("entity-1",)
    assert result.unsupported_entity_ids == ("unknown-entity",)
    assert len(result.issues) == 1


def test_multiple_unsupported_references_are_detected(
    agent,
    response,
    context,
):
    modified_response = ReasoningResponse(
        question=response.question,
        answer=response.answer,
        intent=response.intent,
        source_files=("unknown.py",),
        entity_ids=("unknown-entity",),
        provider_name=response.provider_name,
        model_name=response.model_name,
        evidence_sufficient=True,
    )

    result = agent.validate(modified_response, context)

    assert result.is_valid is False
    assert result.unsupported_source_files == ("unknown.py",)
    assert result.unsupported_entity_ids == ("unknown-entity",)
    assert len(result.issues) == 2


def test_empty_response_references_are_valid(
    agent,
    context,
):
    empty_response = ReasoningResponse(
        question="Explain the application architecture",
        answer="There is insufficient repository evidence.",
        intent=QueryIntent.ARCHITECTURE,
        source_files=(),
        entity_ids=(),
        provider_name="openai",
        model_name="gpt-4o",
        evidence_sufficient=False,
    )

    result = agent.validate(empty_response, context)

    assert result.is_valid is True
    assert result.evidence_sufficient is False
    assert result.supported_source_files == ()
    assert result.supported_entity_ids == ()
    assert result.issues == ()


def test_insufficient_evidence_status_is_preserved(
    agent,
    context,
):
    insufficient_response = ReasoningResponse(
        question="Explain the application architecture",
        answer="There is insufficient repository evidence.",
        intent=QueryIntent.ARCHITECTURE,
        source_files=(),
        entity_ids=(),
        provider_name="openai",
        model_name="gpt-4o",
        evidence_sufficient=False,
    )

    result = agent.validate(insufficient_response, context)

    assert result.evidence_sufficient is False


def test_evidence_sufficiency_is_preserved_when_references_are_valid(
    agent,
    response,
    context,
):
    result = agent.validate(response, context)

    assert result.evidence_sufficient == response.evidence_sufficient


def test_context_with_no_references_rejects_response_references(
    agent,
    response,
):
    context_text = "No repository references"

    empty_context = ContextBuildResult(
        question="Explain the application architecture",
        intent="architecture",
        sections=(),
        context_text=context_text,
        source_files=(),
        entity_ids=(),
        character_count=len(context_text),
        max_characters=12000,
        truncated=False,
    )

    result = agent.validate(response, empty_context)

    assert result.is_valid is False
    assert len(result.unsupported_source_files) == 2
    assert len(result.unsupported_entity_ids) == 2


def test_context_can_contain_additional_unused_references(
    agent,
    response,
    context,
):
    expanded_context = ContextBuildResult(
        question=context.question,
        intent=context.intent,
        sections=context.sections,
        context_text=context.context_text,
        source_files=context.source_files + ("appy/config.py",),
        entity_ids=context.entity_ids + ("entity-3",),
        character_count=context.character_count,
        max_characters=context.max_characters,
        truncated=context.truncated,
    )

    result = agent.validate(response, expanded_context)

    assert result.is_valid is True
    assert result.supported_source_files == response.source_files
    assert result.supported_entity_ids == response.entity_ids


def test_response_must_be_reasoning_response_instance(
    agent,
    context,
):
    with pytest.raises(
        EvidenceValidationError,
        match="response must be a ReasoningResponse",
    ):
        agent.validate(object(), context)


def test_context_must_be_context_build_result_instance(
    agent,
    response,
):
    with pytest.raises(
        EvidenceValidationError,
        match="context must be a ContextBuildResult",
    ):
        agent.validate(response, object())


def test_response_source_files_must_be_tuple(
    agent,
    response,
    context,
):
    object.__setattr__(
        response,
        "source_files",
        ["appy/main.py"],
    )

    with pytest.raises(
        EvidenceValidationError,
        match="Response source_files must be a tuple",
    ):
        agent.validate(response, context)


def test_response_entity_ids_must_be_tuple(
    agent,
    response,
    context,
):
    object.__setattr__(
        response,
        "entity_ids",
        ["entity-1"],
    )

    with pytest.raises(
        EvidenceValidationError,
        match="Response entity_ids must be a tuple",
    ):
        agent.validate(response, context)


def test_context_source_files_must_be_tuple(
    agent,
    response,
    context,
):
    object.__setattr__(
        context,
        "source_files",
        ["appy/main.py"],
    )

    with pytest.raises(
        EvidenceValidationError,
        match="Context source_files must be a tuple",
    ):
        agent.validate(response, context)


def test_context_entity_ids_must_be_tuple(
    agent,
    response,
    context,
):
    object.__setattr__(
        context,
        "entity_ids",
        ["entity-1"],
    )

    with pytest.raises(
        EvidenceValidationError,
        match="Context entity_ids must be a tuple",
    ):
        agent.validate(response, context)


def test_result_is_immutable(
    agent,
    response,
    context,
):
    result = agent.validate(response, context)

    with pytest.raises(FrozenInstanceError):
        result.is_valid = False


def test_result_contains_tuple_collections(
    agent,
    response,
    context,
):
    result = agent.validate(response, context)

    assert isinstance(result.supported_source_files, tuple)
    assert isinstance(result.unsupported_source_files, tuple)
    assert isinstance(result.supported_entity_ids, tuple)
    assert isinstance(result.unsupported_entity_ids, tuple)
    assert isinstance(result.issues, tuple)





def test_duplicate_supported_references_are_normalized(
    agent,
    context,
):
    duplicate_response = ReasoningResponse(
        question="Explain the application architecture",
        answer="The application uses a layered architecture.",
        intent=QueryIntent.ARCHITECTURE,
        source_files=(
            "appy/main.py",
            "appy/main.py",
        ),
        entity_ids=(
            "entity-1",
            "entity-1",
        ),
        provider_name="openai",
        model_name="gpt-4o",
        evidence_sufficient=True,
    )

    result = agent.validate(duplicate_response, context)

    assert result.is_valid is True
    assert result.supported_source_files == ("appy/main.py",)
    assert result.supported_entity_ids == ("entity-1",)
    assert result.unsupported_source_files == ()
    assert result.unsupported_entity_ids == ()



def test_validation_does_not_modify_response(
    agent,
    response,
    context,
):
    original_source_files = response.source_files
    original_entity_ids = response.entity_ids
    original_answer = response.answer

    agent.validate(response, context)

    assert response.source_files == original_source_files
    assert response.entity_ids == original_entity_ids
    assert response.answer == original_answer
