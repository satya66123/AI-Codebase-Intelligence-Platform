
import pytest

from appy.application.context_builder import ContextBuildResult
from appy.application.evidence_validation_agent import (
    EvidenceValidationResult,
)
from appy.application.intent_detection_service import QueryIntent
from appy.application.reasoning_response_model import ReasoningResponse
from appy.application.ai_answer_quality_evaluation_service import (
    AIAnswerQualityEvaluationError,
    AIAnswerQualityEvaluationResult,
    AIAnswerQualityEvaluationService,
    AnswerQualityDimension,
    AnswerQualityLevel,
)


def create_response(
    question="How does the user service work?",
    answer=(
        "The user service manages user operations. "
        "It creates users and retrieves user information "
        "through the application service layer."
    ),
    source_files=("appy/services/user_service.py",),
    entity_ids=("entity-1",),
    evidence_sufficient=True,
):
    return ReasoningResponse(
        question=question,
        answer=answer,
        intent=next(iter(QueryIntent)),
        source_files=source_files,
        entity_ids=entity_ids,
        provider_name="openai",
        model_name="test-model",
        evidence_sufficient=evidence_sufficient,
    )


def create_context(
    context_text="UserService manages user creation and retrieval.",
    source_files=("appy/services/user_service.py",),
    entity_ids=("entity-1",),
):
    return ContextBuildResult(
        question="How does the user service work?",
        intent="EXPLANATION",
        sections=(),
        context_text=context_text,
        source_files=source_files,
        entity_ids=entity_ids,
        character_count=len(context_text),
        max_characters=12000,
        truncated=False,
    )


def create_evidence_result(
    is_valid=True,
    evidence_sufficient=True,
    supported_source_files=("appy/services/user_service.py",),
    unsupported_source_files=(),
    supported_entity_ids=("entity-1",),
    unsupported_entity_ids=(),
    issues=(),
):
    return EvidenceValidationResult(
        is_valid=is_valid,
        evidence_sufficient=evidence_sufficient,
        supported_source_files=supported_source_files,
        unsupported_source_files=unsupported_source_files,
        supported_entity_ids=supported_entity_ids,
        unsupported_entity_ids=unsupported_entity_ids,
        issues=issues,
    )


def evaluate(
    response=None,
    context=None,
    evidence_result=None,
):
    service = AIAnswerQualityEvaluationService()

    return service.evaluate(
        response or create_response(),
        context or create_context(),
        evidence_result or create_evidence_result(),
    )


def test_evaluate_returns_structured_result():
    result = evaluate()

    assert isinstance(
        result,
        AIAnswerQualityEvaluationResult,
    )
    assert result.question == "How does the user service work?"
    assert result.total_reference_count == 2


def test_evaluate_returns_all_four_dimensions():
    result = evaluate()

    assert isinstance(result.relevance, AnswerQualityDimension)
    assert isinstance(result.completeness, AnswerQualityDimension)
    assert isinstance(result.clarity, AnswerQualityDimension)
    assert isinstance(
        result.evidence_grounding,
        AnswerQualityDimension,
    )
    assert len(result.dimensions) == 4


def test_evaluate_scores_are_within_valid_range():
    result = evaluate()

    for dimension in result.dimensions:
        assert 0.0 <= dimension.score <= 100.0

    assert 0.0 <= result.overall_score <= 100.0


def test_evaluate_uses_configured_dimension_weights():
    result = evaluate()

    expected = round(
        result.relevance.score * 0.30
        + result.completeness.score * 0.20
        + result.clarity.score * 0.20
        + result.evidence_grounding.score * 0.30,
        2,
    )

    assert result.overall_score == expected


def test_evaluate_returns_question_from_response():
    response = create_response(
        question="Where is authentication implemented?"
    )

    result = evaluate(response=response)

    assert result.question == (
        "Where is authentication implemented?"
    )


def test_relevance_score_is_high_for_matching_keywords():
    response = create_response(
        question="How does the user service manage user operations?",
        answer=(
            "The user service manages user operations. "
            "It creates users and retrieves user information."
        ),
    )

    result = evaluate(response=response)

    assert result.relevance.score >= 70.0


def test_relevance_score_is_low_for_unrelated_answer():
    response = create_response(
        question="How does authentication validate tokens?",
        answer=(
            "The weather forecast predicts rain tomorrow. "
            "Clouds are expected throughout the afternoon."
        ),
    )

    result = evaluate(response=response)

    assert result.relevance.score == 0.0


def test_relevance_reports_missing_keyword_overlap():
    response = create_response(
        question="Explain authentication middleware",
        answer="The application handles database transactions.",
    )

    result = evaluate(response=response)

    assert any(
        "does not share meaningful keywords" in finding
        for finding in result.relevance.findings
    )


def test_relevance_handles_question_without_meaningful_tokens():
    response = create_response(
        question="How is it?",
        answer="The application performs user operations.",
    )

    result = evaluate(response=response)

    assert result.relevance.score == 50.0
    assert any(
        "insufficient meaningful tokens" in finding
        for finding in result.relevance.findings
    )


def test_completeness_scores_very_short_answer_low():
    response = create_response(
        answer="It works.",
        source_files=(),
        entity_ids=(),
    )

    result = evaluate(
        response=response,
        evidence_result=create_evidence_result(
            supported_source_files=(),
            supported_entity_ids=(),
        ),
    )

    assert result.completeness.score == 20.0


def test_completeness_scores_short_answer():
    response = create_response(
        answer="The service manages user operations.",
    )

    result = evaluate(response=response)

    assert result.completeness.score == 45.0


def test_completeness_scores_medium_answer():
    response = create_response(
        answer=(
            "The service manages user operations and coordinates "
            "the application workflow across application modules "
            "while validating incoming requests."
        ),
    )

    result = evaluate(response=response)

    assert result.completeness.score == 65.0


def test_completeness_scores_detailed_answer():
    response = create_response(
        answer=(
            "The user service manages user operations across the "
            "application. It provides methods for creating, updating, "
            "retrieving, and deleting user records. The service coordinates "
            "validation and delegates persistence operations to the "
            "repository layer. This keeps application responsibilities "
            "separate from database implementation details."
        ),
    )

    result = evaluate(response=response)

    assert result.completeness.score == 80.0


def test_completeness_penalizes_long_single_sentence():
    response = create_response(
        answer=(
            "The user service manages user operations and creates records "
            "while validating input and coordinating repository access "
            "and handling application requests through several methods "
            "that provide consistent behavior across the application layer."
        ),
    )

    result = evaluate(response=response)

    assert result.completeness.score < 95.0


def test_completeness_penalizes_missing_punctuation():
    response = create_response(
        answer=(
            "The user service manages user operations and coordinates "
            "application requests"
        ),
    )

    result = evaluate(response=response)

    assert any(
        "punctuation" in finding
        for finding in result.completeness.findings
    )


def test_clarity_scores_readable_answer():
    response = create_response(
        answer=(
            "The service manages users. "
            "It validates incoming requests. "
            "It delegates database operations."
        ),
    )

    result = evaluate(response=response)

    assert result.clarity.score == 100.0


def test_clarity_penalizes_very_long_sentences():
    response = create_response(
        answer=(
            "The service manages users and validates incoming requests "
            "while coordinating database operations and application "
            "workflows through several internal methods that interact "
            "with multiple modules and provide consistent behavior "
            "across the entire application architecture while also "
            "handling repository operations and coordinating additional "
            "application responsibilities across different service layers."
        ),
    )

    result = evaluate(response=response)

    assert result.clarity.score < 100.0
    assert any(
        "very long" in finding
        for finding in result.clarity.findings
    )


def test_clarity_detects_repeated_words():
    response = create_response(
        answer=(
            "The authentication authentication authentication "
            "authentication service validates requests."
        ),
    )

    result = evaluate(response=response)

    assert any(
        "repeated words" in finding
        for finding in result.clarity.findings
    )


def test_clarity_recognizes_paragraph_breaks():
    response = create_response(
        answer=(
            "The service manages users.\n\n"
            "It validates incoming requests."
        ),
    )

    result = evaluate(response=response)

    assert any(
        "paragraph breaks" in finding
        for finding in result.clarity.findings
    )


def test_evidence_grounding_scores_supported_references():
    result = evaluate()

    assert result.evidence_grounding.score == 100.0
    assert result.supported_reference_count == 2
    assert result.unsupported_reference_count == 0


def test_evidence_grounding_penalizes_unsupported_references():
    evidence = create_evidence_result(
        is_valid=False,
        supported_source_files=("appy.py",),
        unsupported_source_files=("unknown.py",),
        supported_entity_ids=("entity-1",),
        issues=("Unsupported source file.",),
    )

    result = evaluate(evidence_result=evidence)

    assert result.evidence_grounding.score == 50.0
    assert result.unsupported_reference_count == 1
    assert result.has_evidence_issues is True


def test_evidence_grounding_scores_zero_when_no_references_exist():
    evidence = create_evidence_result(
        supported_source_files=(),
        supported_entity_ids=(),
    )

    response = create_response(
        source_files=(),
        entity_ids=(),
    )

    result = evaluate(
        response=response,
        evidence_result=evidence,
    )

    assert result.evidence_grounding.score == 30.0
    assert result.total_reference_count == 0


def test_evidence_grounding_caps_score_when_evidence_insufficient():
    evidence = create_evidence_result(
        evidence_sufficient=False,
    )

    result = evaluate(evidence_result=evidence)

    assert result.evidence_grounding.score <= 40.0
    assert result.has_evidence_issues is True


def test_evidence_grounding_uses_response_evidence_flag():
    response = create_response(
        evidence_sufficient=False,
    )

    result = evaluate(response=response)

    assert result.evidence_grounding.score <= 40.0
    assert result.evidence_sufficient is False


def test_evidence_grounding_caps_score_for_invalid_validation():
    evidence = create_evidence_result(
        is_valid=False,
        supported_source_files=("appy.py",),
        unsupported_source_files=(),
        supported_entity_ids=("entity-1",),
        issues=("Validation failed.",),
    )

    result = evaluate(evidence_result=evidence)

    assert result.evidence_grounding.score <= 50.0


def test_evidence_grounding_reports_empty_context():
    context = create_context(context_text="")

    result = evaluate(context=context)

    assert result.evidence_grounding.score <= 30.0
    assert any(
        "no textual evidence" in finding
        for finding in result.evidence_grounding.findings
    )


def test_result_reports_reference_counts():
    evidence = create_evidence_result(
        supported_source_files=("appy.py", "services/user.py"),
        unsupported_source_files=("missing.py",),
        supported_entity_ids=("entity-1", "entity-2"),
        unsupported_entity_ids=("entity-3",),
    )

    result = evaluate(evidence_result=evidence)

    assert result.supported_reference_count == 4
    assert result.unsupported_reference_count == 2
    assert result.total_reference_count == 6


def test_result_reports_evidence_sufficiency():
    result = evaluate()

    assert result.evidence_sufficient is True


def test_result_combines_findings_from_dimensions():
    result = evaluate()

    expected_findings = tuple(
        finding
        for dimension in result.dimensions
        for finding in dimension.findings
    )

    assert result.findings == expected_findings


def test_result_acceptability_uses_sixty_point_threshold():
    result = evaluate()

    assert result.is_acceptable == (
        result.overall_score >= 60.0
    )


def test_quality_level_excellent_threshold():
    assert (
        AIAnswerQualityEvaluationService._determine_quality_level(85.0)
        == AnswerQualityLevel.EXCELLENT
    )


def test_quality_level_good_threshold():
    assert (
        AIAnswerQualityEvaluationService._determine_quality_level(70.0)
        == AnswerQualityLevel.GOOD
    )


def test_quality_level_fair_threshold():
    assert (
        AIAnswerQualityEvaluationService._determine_quality_level(50.0)
        == AnswerQualityLevel.FAIR
    )


def test_quality_level_poor_threshold():
    assert (
        AIAnswerQualityEvaluationService._determine_quality_level(49.99)
        == AnswerQualityLevel.POOR
    )


def test_evaluate_rejects_invalid_response():
    service = AIAnswerQualityEvaluationService()

    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="ReasoningResponse",
    ):
        service.evaluate(
            "invalid",
            create_context(),
            create_evidence_result(),
        )


def test_evaluate_rejects_invalid_context():
    service = AIAnswerQualityEvaluationService()

    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="ContextBuildResult",
    ):
        service.evaluate(
            create_response(),
            "invalid",
            create_evidence_result(),
        )


def test_evaluate_rejects_invalid_evidence_result():
    service = AIAnswerQualityEvaluationService()

    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="EvidenceValidationResult",
    ):
        service.evaluate(
            create_response(),
            create_context(),
            "invalid",
        )


def test_dimension_rejects_empty_name():
    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="Dimension name",
    ):
        AnswerQualityDimension(
            name="",
            score=80.0,
            weight=0.25,
            findings=(),
        )


@pytest.mark.parametrize(
    "score",
    [
        -1,
        101,
        "80",
        True,
    ],
)
def test_dimension_rejects_invalid_score(score):
    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="Dimension score",
    ):
        AnswerQualityDimension(
            name="clarity",
            score=score,
            weight=0.25,
            findings=(),
        )


@pytest.mark.parametrize(
    "weight",
    [
        -0.1,
        1.1,
        "0.2",
        True,
    ],
)
def test_dimension_rejects_invalid_weight(weight):
    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="Dimension weight",
    ):
        AnswerQualityDimension(
            name="clarity",
            score=80.0,
            weight=weight,
            findings=(),
        )


def test_dimension_rejects_non_tuple_findings():
    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="findings must be a tuple",
    ):
        AnswerQualityDimension(
            name="clarity",
            score=80.0,
            weight=0.25,
            findings=["Invalid finding"],
        )


def test_dimension_rejects_empty_finding():
    with pytest.raises(
        AIAnswerQualityEvaluationError,
        match="non-empty strings",
    ):
        AnswerQualityDimension(
            name="clarity",
            score=80.0,
            weight=0.25,
            findings=("",),
        )


def test_evaluate_is_deterministic():
    response = create_response()
    context = create_context()
    evidence = create_evidence_result()

    service = AIAnswerQualityEvaluationService()

    first = service.evaluate(
        response,
        context,
        evidence,
    )

    second = service.evaluate(
        response,
        context,
        evidence,
    )

    assert first == second


def test_evaluate_does_not_modify_response():
    response = create_response()
    original_question = response.question
    original_answer = response.answer
    original_source_files = response.source_files

    evaluate(response=response)

    assert response.question == original_question
    assert response.answer == original_answer
    assert response.source_files == original_source_files


def test_evaluate_does_not_modify_context():
    context = create_context()

    original_text = context.context_text
    original_files = context.source_files
    original_entities = context.entity_ids

    evaluate(context=context)

    assert context.context_text == original_text
    assert context.source_files == original_files
    assert context.entity_ids == original_entities


def test_evaluate_reports_supported_and_unsupported_entity_references():
    evidence = create_evidence_result(
        supported_source_files=("appy.py",),
        unsupported_source_files=(),
        supported_entity_ids=("entity-1",),
        unsupported_entity_ids=("entity-2",),
    )

    result = evaluate(evidence_result=evidence)

    assert result.supported_reference_count == 2
    assert result.unsupported_reference_count == 1
    assert result.has_evidence_issues is True


def test_dimension_weights_sum_to_one():
    total_weight = sum(
        AIAnswerQualityEvaluationService.DIMENSION_WEIGHTS.values()
    )

    assert total_weight == pytest.approx(1.0)
