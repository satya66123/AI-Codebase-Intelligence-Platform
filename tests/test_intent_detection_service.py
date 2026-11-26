
import pytest

from appy.application.intent_detection_service import (
    IntentDetectionError,
    IntentDetectionResult,
    IntentDetectionService,
    QueryIntent,
)
from appy.application.question_validation_service import (
    QuestionValidationService,
    ValidatedQuestion,
)


@pytest.fixture
def service():
    return IntentDetectionService()


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        (
            "Explain the project architecture.",
            QueryIntent.ARCHITECTURE,
        ),
        (
            "Where is authentication implemented?",
            QueryIntent.FILE_LOCATION,
        ),
        (
            "Which file contains the login function?",
            QueryIntent.FILE_LOCATION,
        ),
        (
            "Explain how the authentication function works.",
            QueryIntent.CODE_EXPLANATION,
        ),
        (
            "What does this class do?",
            QueryIntent.CODE_EXPLANATION,
        ),
        (
            "Which files depend on this service?",
            QueryIntent.DEPENDENCY,
        ),
        (
            "Show the dependencies of this module.",
            QueryIntent.DEPENDENCY,
        ),
        (
            "What calls this function?",
            QueryIntent.CALL_RELATIONSHIP,
        ),
        (
            "Who calls the authentication method?",
            QueryIntent.CALL_RELATIONSHIP,
        ),
        (
            "Explain the data flow from API to storage.",
            QueryIntent.DATA_FLOW,
        ),
        (
            "How does data move through the application?",
            QueryIntent.DATA_FLOW,
        ),
        (
            "Explain the execution flow.",
            QueryIntent.EXECUTION_FLOW,
        ),
        (
            "Show the runtime flow.",
            QueryIntent.EXECUTION_FLOW,
        ),
        (
            "Where is the database configuration?",
            QueryIntent.CONFIGURATION,
        ),
        (
            "Which environment variable controls the database?",
            QueryIntent.CONFIGURATION,
        ),
        (
            "What happens if I modify this module?",
            QueryIntent.CHANGE_IMPACT,
        ),
        (
            "What is the impact of changing this function?",
            QueryIntent.CHANGE_IMPACT,
        ),
        (
            "Give me an overview of this repository.",
            QueryIntent.GENERAL_CODEBASE,
        ),
        (
            "What does this project contain?",
            QueryIntent.GENERAL_CODEBASE,
        ),
        (
            "Tell me something interesting.",
            QueryIntent.UNKNOWN,
        ),
    ],
)
def test_detects_expected_intent(
    service,
    question,
    expected_intent,
):
    result = service.detect(question)

    assert isinstance(result, IntentDetectionResult)
    assert result.intent == expected_intent
    assert result.question == question


def test_detect_accepts_validated_question(service):
    validated = QuestionValidationService().validate(
        "Explain the project architecture."
    )

    result = service.detect(validated)

    assert result.intent == QueryIntent.ARCHITECTURE
    assert result.question == validated.question


def test_detect_normalizes_raw_question(service):
    result = service.detect(
        "   Explain the project architecture.   "
    )

    assert result.question == "Explain the project architecture."
    assert result.intent == QueryIntent.ARCHITECTURE


def test_detect_returns_confidence_for_matched_intent(service):
    result = service.detect("Explain the project architecture.")

    assert result.confidence == 0.90
    assert result.matched_terms


def test_detect_returns_zero_confidence_for_unknown_intent(service):
    result = service.detect("Tell me something interesting.")

    assert result.intent == QueryIntent.UNKNOWN
    assert result.confidence == 0.0
    assert result.matched_terms == ()


def test_detect_returns_general_intent_confidence(service):
    result = service.detect("Give me an overview of this repository.")

    assert result.intent == QueryIntent.GENERAL_CODEBASE
    assert result.confidence == 0.80


@pytest.mark.parametrize(
    "question",
    [
        "",
        " ",
        None,
        123,
        [],
        {},
    ],
)
def test_detect_rejects_invalid_questions(service, question):
    with pytest.raises(IntentDetectionError):
        service.detect(question)


def test_service_rejects_invalid_question_validator():
    with pytest.raises(IntentDetectionError):
        IntentDetectionService(question_validator="invalid")


def test_result_rejects_empty_question():
    with pytest.raises(IntentDetectionError):
        IntentDetectionResult(
            question=" ",
            intent=QueryIntent.UNKNOWN,
            confidence=0.0,
            matched_terms=(),
        )


def test_result_rejects_invalid_intent():
    with pytest.raises(IntentDetectionError):
        IntentDetectionResult(
            question="Explain this code.",
            intent="invalid",
            confidence=0.5,
            matched_terms=(),
        )


@pytest.mark.parametrize(
    "confidence",
    [-0.1, 1.1, True, "0.5", None],
)
def test_result_rejects_invalid_confidence(confidence):
    with pytest.raises(IntentDetectionError):
        IntentDetectionResult(
            question="Explain this code.",
            intent=QueryIntent.CODE_EXPLANATION,
            confidence=confidence,
            matched_terms=(),
        )


def test_result_rejects_non_tuple_matched_terms():
    with pytest.raises(IntentDetectionError):
        IntentDetectionResult(
            question="Explain this code.",
            intent=QueryIntent.CODE_EXPLANATION,
            confidence=0.9,
            matched_terms=["explain"],
        )


def test_result_rejects_empty_matched_term():
    with pytest.raises(IntentDetectionError):
        IntentDetectionResult(
            question="Explain this code.",
            intent=QueryIntent.CODE_EXPLANATION,
            confidence=0.9,
            matched_terms=("",),
        )


def test_detect_is_case_insensitive(service):
    result = service.detect(
        "EXPLAIN THE PROJECT ARCHITECTURE."
    )

    assert result.intent == QueryIntent.ARCHITECTURE


def test_detect_preserves_question_text(service):
    question = "Explain the data flow\nfrom API to storage."

    result = service.detect(question)

    assert result.question == question
    assert result.intent == QueryIntent.DATA_FLOW
