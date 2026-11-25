
import pytest

from app.application.question_analysis_agent import (
    QuestionAnalysisAgent,
    QuestionAnalysisError,
    QuestionAnalysisResult,
)
from app.application.question_validation_service import (
    QuestionValidationService,
)
from app.application.intent_detection_service import (
    IntentDetectionService,
    QueryIntent,
)


@pytest.fixture
def agent():
    return QuestionAnalysisAgent()


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
            "Explain how this function works.",
            QueryIntent.CODE_EXPLANATION,
        ),
        (
            "Which modules depend on this service?",
            QueryIntent.DEPENDENCY,
        ),
        (
            "What calls this function?",
            QueryIntent.CALL_RELATIONSHIP,
        ),
        (
            "Explain the data flow.",
            QueryIntent.DATA_FLOW,
        ),
        (
            "Show the execution flow.",
            QueryIntent.EXECUTION_FLOW,
        ),
        (
            "Where is the database configuration?",
            QueryIntent.CONFIGURATION,
        ),
        (
            "What happens if I modify this module?",
            QueryIntent.CHANGE_IMPACT,
        ),
        (
            "Give me an overview of this repository.",
            QueryIntent.GENERAL_CODEBASE,
        ),
        (
            "Tell me something interesting.",
            QueryIntent.UNKNOWN,
        ),
    ],
)
def test_analyze_detects_expected_intent(
    agent,
    question,
    expected_intent,
):
    result = agent.analyze(question)

    assert isinstance(result, QuestionAnalysisResult)
    assert result.intent == expected_intent
    assert result.question == question


def test_analyze_returns_confidence(agent):
    result = agent.analyze(
        "Explain the project architecture."
    )

    assert result.confidence == 0.90


def test_analyze_returns_matched_terms(agent):
    result = agent.analyze(
        "Explain the project architecture."
    )

    assert result.matched_terms
    assert "architecture" in result.matched_terms


def test_analyze_unknown_question_has_zero_confidence(agent):
    result = agent.analyze(
        "Tell me something interesting."
    )

    assert result.intent == QueryIntent.UNKNOWN
    assert result.confidence == 0.0
    assert result.matched_terms == ()


def test_analyze_trims_question(agent):
    result = agent.analyze(
        "   Explain the project architecture.   "
    )

    assert result.question == "Explain the project architecture."
    assert result.intent == QueryIntent.ARCHITECTURE


def test_analyze_preserves_question_case(agent):
    question = "EXPLAIN THE PROJECT ARCHITECTURE."

    result = agent.analyze(question)

    assert result.question == question
    assert result.intent == QueryIntent.ARCHITECTURE


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
def test_analyze_rejects_invalid_questions(agent, question):
    with pytest.raises(QuestionAnalysisError):
        agent.analyze(question)


def test_agent_accepts_custom_question_validator():
    validator = QuestionValidationService(max_length=100)

    agent = QuestionAnalysisAgent(
        question_validator=validator
    )

    result = agent.analyze(
        "Explain the project architecture."
    )

    assert result.intent == QueryIntent.ARCHITECTURE


def test_agent_accepts_custom_intent_detector():
    validator = QuestionValidationService()
    detector = IntentDetectionService(
        question_validator=validator
    )

    agent = QuestionAnalysisAgent(
        question_validator=validator,
        intent_detector=detector,
    )

    result = agent.analyze(
        "Where is authentication implemented?"
    )

    assert result.intent == QueryIntent.FILE_LOCATION


def test_agent_rejects_invalid_validator():
    with pytest.raises(QuestionAnalysisError):
        QuestionAnalysisAgent(
            question_validator="invalid"
        )


def test_agent_rejects_invalid_intent_detector():
    with pytest.raises(QuestionAnalysisError):
        QuestionAnalysisAgent(
            intent_detector="invalid"
        )


def test_result_rejects_empty_question():
    with pytest.raises(QuestionAnalysisError):
        QuestionAnalysisResult(
            question=" ",
            intent=QueryIntent.UNKNOWN,
            confidence=0.0,
            matched_terms=(),
        )


def test_result_rejects_invalid_intent():
    with pytest.raises(QuestionAnalysisError):
        QuestionAnalysisResult(
            question="Explain the code.",
            intent="invalid",
            confidence=0.5,
            matched_terms=(),
        )


@pytest.mark.parametrize(
    "confidence",
    [-0.1, 1.1, True, "0.5", None],
)
def test_result_rejects_invalid_confidence(confidence):
    with pytest.raises(QuestionAnalysisError):
        QuestionAnalysisResult(
            question="Explain the code.",
            intent=QueryIntent.CODE_EXPLANATION,
            confidence=confidence,
            matched_terms=(),
        )


def test_result_rejects_non_tuple_matched_terms():
    with pytest.raises(QuestionAnalysisError):
        QuestionAnalysisResult(
            question="Explain the code.",
            intent=QueryIntent.CODE_EXPLANATION,
            confidence=0.9,
            matched_terms=["explain"],
        )


def test_result_rejects_empty_matched_term():
    with pytest.raises(QuestionAnalysisError):
        QuestionAnalysisResult(
            question="Explain the code.",
            intent=QueryIntent.CODE_EXPLANATION,
            confidence=0.9,
            matched_terms=("",),
        )


# noinspection dataclass
def test_result_is_immutable():
    result = QuestionAnalysisResult(
        question="Explain the project architecture.",
        intent=QueryIntent.ARCHITECTURE,
        confidence=0.9,
        matched_terms=("architecture",),
    )

    with pytest.raises(AttributeError):
        result.question = "Changed question"
