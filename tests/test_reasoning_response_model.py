
from dataclasses import FrozenInstanceError

import pytest

from appy.application.intent_detection_service import QueryIntent
from appy.application.reasoning_response_model import (
    ReasoningResponse,
    ReasoningResponseError,
)


@pytest.fixture
def response():
    return ReasoningResponse(
        question="Explain the UserService class.",
        answer="UserService manages user-related operations.",
        intent=QueryIntent.CODE_EXPLANATION,
        source_files=("appy/services/user_service.py",),
        entity_ids=("user-service",),
        provider_name="OpenAI",
        model_name="gpt-5-mini",
        evidence_sufficient=True,
    )


def test_creates_reasoning_response(response):
    assert isinstance(response, ReasoningResponse)


def test_stores_question(response):
    assert response.question == "Explain the UserService class."


def test_stores_answer(response):
    assert response.answer == (
        "UserService manages user-related operations."
    )


def test_stores_intent(response):
    assert response.intent == QueryIntent.CODE_EXPLANATION


def test_stores_source_files(response):
    assert response.source_files == (
        "appy/services/user_service.py",
    )


def test_stores_entity_ids(response):
    assert response.entity_ids == ("user-service",)


def test_stores_provider_name(response):
    assert response.provider_name == "openai"


def test_stores_model_name(response):
    assert response.model_name == "gpt-5-mini"


def test_stores_evidence_status(response):
    assert response.evidence_sufficient is True


def test_normalizes_question_and_answer_whitespace():
    result = ReasoningResponse(
        question="  Explain the repository.  ",
        answer="  Repository explanation.  ",
        intent=QueryIntent.GENERAL_CODEBASE,
    )

    assert result.question == "Explain the repository."
    assert result.answer == "Repository explanation."


def test_normalizes_provider_name():
    result = ReasoningResponse(
        question="Explain the repository.",
        answer="Repository explanation.",
        intent=QueryIntent.GENERAL_CODEBASE,
        provider_name="  OpenAI  ",
    )

    assert result.provider_name == "openai"


def test_normalizes_model_name():
    result = ReasoningResponse(
        question="Explain the repository.",
        answer="Repository explanation.",
        intent=QueryIntent.GENERAL_CODEBASE,
        model_name="  gpt-5-mini  ",
    )

    assert result.model_name == "gpt-5-mini"


def test_accepts_list_references():
    result = ReasoningResponse(
        question="Explain the repository.",
        answer="Repository explanation.",
        intent=QueryIntent.GENERAL_CODEBASE,
        source_files=["appy/main.py"],
        entity_ids=["main-function"],
    )

    assert result.source_files == ("appy/main.py",)
    assert result.entity_ids == ("main-function",)


def test_deduplicates_source_files():
    result = ReasoningResponse(
        question="Explain the repository.",
        answer="Repository explanation.",
        intent=QueryIntent.GENERAL_CODEBASE,
        source_files=(
            "appy/main.py",
            "appy/main.py",
            "appy/services/user.py",
        ),
    )

    assert result.source_files == (
        "appy/main.py",
        "appy/services/user.py",
    )


def test_deduplicates_entity_ids():
    result = ReasoningResponse(
        question="Explain the repository.",
        answer="Repository explanation.",
        intent=QueryIntent.GENERAL_CODEBASE,
        entity_ids=("user-service", "user-service", "main"),
    )

    assert result.entity_ids == ("user-service", "main")


def test_empty_references_are_supported():
    result = ReasoningResponse(
        question="Explain the repository.",
        answer="Insufficient repository evidence.",
        intent=QueryIntent.GENERAL_CODEBASE,
        evidence_sufficient=False,
    )

    assert result.source_files == ()
    assert result.entity_ids == ()
    assert result.evidence_sufficient is False


@pytest.mark.parametrize(
    "question",
    ["", " ", None, 123],
)
def test_rejects_invalid_question(question):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question=question,
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
        )


@pytest.mark.parametrize(
    "answer",
    ["", " ", None, 123],
)
def test_rejects_invalid_answer(answer):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer=answer,
            intent=QueryIntent.GENERAL_CODEBASE,
        )


@pytest.mark.parametrize(
    "intent",
    [None, "CODE_EXPLANATION", "unknown", 123],
)
def test_rejects_invalid_intent(intent):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=intent,
        )


@pytest.mark.parametrize(
    "source_files",
    [None, "appy/main.py", 123, {"file": "appy/main.py"}],
)
def test_rejects_invalid_source_files(source_files):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
            source_files=source_files,
        )


@pytest.mark.parametrize(
    "entity_ids",
    [None, "user-service", 123, {"id": "user-service"}],
)
def test_rejects_invalid_entity_ids(entity_ids):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
            entity_ids=entity_ids,
        )


@pytest.mark.parametrize(
    "references",
    [
        ("",),
        (" ",),
        (None,),
        (123,),
    ],
)
def test_rejects_invalid_source_file_entries(references):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
            source_files=references,
        )


@pytest.mark.parametrize(
    "references",
    [
        ("",),
        (" ",),
        (None,),
        (123,),
    ],
)
def test_rejects_invalid_entity_id_entries(references):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
            entity_ids=references,
        )


@pytest.mark.parametrize(
    "provider_name",
    [None, 123, [], {}],
)
def test_rejects_invalid_provider_name(provider_name):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
            provider_name=provider_name,
        )


@pytest.mark.parametrize(
    "model_name",
    [None, 123, [], {}],
)
def test_rejects_invalid_model_name(model_name):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
            model_name=model_name,
        )


@pytest.mark.parametrize(
    "evidence_sufficient",
    ["true", 1, None, [], {}],
)
def test_rejects_invalid_evidence_status(evidence_sufficient):
    with pytest.raises(ReasoningResponseError):
        ReasoningResponse(
            question="Valid question.",
            answer="Valid answer.",
            intent=QueryIntent.GENERAL_CODEBASE,
            evidence_sufficient=evidence_sufficient,
        )


def test_response_is_immutable(response):
    with pytest.raises(FrozenInstanceError):
        response.answer = "Changed answer."


def test_to_dict_returns_dictionary(response):
    result = response.to_dict()

    assert isinstance(result, dict)


def test_to_dict_contains_all_fields(response):
    result = response.to_dict()

    assert result == {
        "question": "Explain the UserService class.",
        "answer": "UserService manages user-related operations.",
        "intent": "CODE_EXPLANATION",
        "source_files": ["appy/services/user_service.py"],
        "entity_ids": ["user-service"],
        "provider_name": "openai",
        "model_name": "gpt-5-mini",
        "evidence_sufficient": True,
    }


def test_to_dict_converts_references_to_lists(response):
    result = response.to_dict()

    assert isinstance(result["source_files"], list)
    assert isinstance(result["entity_ids"], list)


def test_to_dict_serializes_intent_as_name(response):
    result = response.to_dict()

    assert result["intent"] == "CODE_EXPLANATION"
    assert isinstance(result["intent"], str)


def test_to_dict_does_not_modify_response(response):
    original_answer = response.answer

    response.to_dict()

    assert response.answer == original_answer


def test_response_supports_insufficient_evidence():
    result = ReasoningResponse(
        question="Explain an unavailable module.",
        answer="The supplied context does not contain enough evidence.",
        intent=QueryIntent.CODE_EXPLANATION,
        evidence_sufficient=False,
    )

    assert result.evidence_sufficient is False
