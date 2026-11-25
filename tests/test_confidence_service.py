
import pytest

from app.application.confidence_service import (
    ConfidenceAssessment,
    ConfidenceLevel,
    ConfidenceService,
    ConfidenceServiceError,
)
from app.application.evidence_validation_agent import (
    EvidenceValidationResult,
)
from app.application.intent_detection_service import QueryIntent
from app.application.reasoning_response_model import ReasoningResponse


@pytest.fixture
def service():
    return ConfidenceService()


@pytest.fixture
def response():
    return ReasoningResponse(
        question="Explain the application architecture",
        answer="The application uses a layered architecture.",
        intent=QueryIntent.ARCHITECTURE,
        source_files=("app/main.py", "app/services/user_service.py"),
        entity_ids=("entity-1",),
        provider_name="openai",
        model_name="gpt-4o",
        evidence_sufficient=True,
    )


def make_validation(
    supported_files=("app/main.py", "app/services/user_service.py"),
    unsupported_files=(),
    supported_entities=("entity-1",),
    unsupported_entities=(),
    is_valid=True,
    evidence_sufficient=True,
    issues=(),
):
    return EvidenceValidationResult(
        is_valid=is_valid,
        evidence_sufficient=evidence_sufficient,
        supported_source_files=supported_files,
        unsupported_source_files=unsupported_files,
        supported_entity_ids=supported_entities,
        unsupported_entity_ids=unsupported_entities,
        issues=issues,
    )


def test_all_references_supported_gives_high_confidence(service, response):
    result = service.assess(response, make_validation())

    assert result.confidence_score == 1.0
    assert result.confidence_level == ConfidenceLevel.HIGH
    assert result.evidence_coverage == 1.0
    assert result.total_references == 3
    assert result.supported_references == 3
    assert result.unsupported_references == 0


def test_all_references_supported_has_no_unsupported_reason(
    service, response
):
    result = service.assess(response, make_validation())

    assert not any(
        "not found" in reason for reason in result.reasons
    )


def test_partial_reference_support_gives_medium_confidence(
    service, response
):
    result = service.assess(
        response,
        make_validation(
            supported_files=("app/main.py",),
            unsupported_files=("app/services/user_service.py",),
            supported_entities=("entity-1",),
        ),
    )

    assert result.confidence_score == pytest.approx(0.8333, abs=0.0001)
    assert result.confidence_level == ConfidenceLevel.HIGH
    assert result.evidence_coverage == pytest.approx(2 / 3, abs=0.0001)


def test_no_supported_references_gives_low_confidence(
    service, response
):
    result = service.assess(
        response,
        make_validation(
            supported_files=(),
            unsupported_files=(
                "app/main.py",
                "app/services/user_service.py",
            ),
            supported_entities=(),
            unsupported_entities=("entity-1",),
        ),
    )

    assert result.confidence_score == 0.5
    assert result.confidence_level == ConfidenceLevel.MEDIUM
    assert result.evidence_coverage == 0.0


def test_no_references_gives_low_confidence(service):
    no_reference_response = ReasoningResponse(
        question="Explain the application architecture",
        answer="The application uses a layered architecture.",
        intent=QueryIntent.ARCHITECTURE,
        source_files=(),
        entity_ids=(),
        provider_name="openai",
        model_name="gpt-4o",
        evidence_sufficient=True,
    )

    result = service.assess(
        no_reference_response,
        make_validation(
            supported_files=(),
            supported_entities=(),
        ),
    )

    assert result.confidence_score == 0.0
    assert result.confidence_level == ConfidenceLevel.LOW
    assert result.total_references == 0
    assert result.evidence_coverage == 0.0


def test_insufficient_response_evidence_caps_confidence(
    service, response
):
    insufficient_response = ReasoningResponse(
        question=response.question,
        answer=response.answer,
        intent=response.intent,
        source_files=response.source_files,
        entity_ids=response.entity_ids,
        provider_name=response.provider_name,
        model_name=response.model_name,
        evidence_sufficient=False,
    )

    result = service.assess(
        insufficient_response,
        make_validation(),
    )

    assert result.confidence_score == 0.49
    assert result.confidence_level == ConfidenceLevel.LOW
    assert any(
        "reasoning response indicates" in reason
        for reason in result.reasons
    )


def test_insufficient_validation_evidence_caps_confidence(
    service, response
):
    result = service.assess(
        response,
        make_validation(evidence_sufficient=False),
    )

    assert result.confidence_score == 0.49
    assert result.confidence_level == ConfidenceLevel.LOW


def test_failed_validation_caps_confidence(service, response):
    result = service.assess(
        response,
        make_validation(is_valid=False),
    )

    assert result.confidence_score == 0.39
    assert result.confidence_level == ConfidenceLevel.LOW


def test_failed_validation_adds_reason(service, response):
    result = service.assess(
        response,
        make_validation(
            is_valid=False,
            issues=("A validation issue was detected.",),
        ),
    )

    assert any(
        "validation failed" in reason for reason in result.reasons
    )
    assert "A validation issue was detected." in result.reasons


def test_unsupported_references_are_counted(service, response):
    result = service.assess(
        response,
        make_validation(
            supported_files=("app/main.py",),
            unsupported_files=("app/services/user_service.py",),
            supported_entities=("entity-1",),
        ),
    )

    assert result.total_references == 3
    assert result.supported_references == 2
    assert result.unsupported_references == 1


def test_validation_issues_are_included_in_reasons(
    service, response
):
    result = service.assess(
        response,
        make_validation(
            issues=("Unknown source reference.",),
        ),
    )

    assert "Unknown source reference." in result.reasons


def test_duplicate_validation_issues_are_not_repeated(
    service, response
):
    result = service.assess(
        response,
        make_validation(
            issues=("A validation issue.", "A validation issue."),
        ),
    )

    assert result.reasons.count("A validation issue.") == 1


def test_assessment_result_is_immutable(service, response):
    result = service.assess(response, make_validation())

    with pytest.raises(AttributeError):
        result.confidence_score = 0.2


def test_invalid_response_type_is_rejected(service):
    with pytest.raises(
        ConfidenceServiceError,
        match="response must be a ReasoningResponse",
    ):
        service.assess(object(), make_validation())


def test_invalid_validation_type_is_rejected(service, response):
    with pytest.raises(
        ConfidenceServiceError,
        match="validation_result must be an EvidenceValidationResult",
    ):
        service.assess(response, object())


@pytest.mark.parametrize(
    "score",
    [-0.1, 1.1, True, "0.5"],
)
def test_assessment_rejects_invalid_confidence_score(score):
    with pytest.raises(ConfidenceServiceError):
        ConfidenceAssessment(
            confidence_score=score,
            confidence_level=ConfidenceLevel.MEDIUM,
            evidence_coverage=0.5,
            total_references=2,
            supported_references=1,
            unsupported_references=1,
            reasons=("Test reason.",),
        )


@pytest.mark.parametrize(
    "coverage",
    [-0.1, 1.1, True, "0.5"],
)
def test_assessment_rejects_invalid_evidence_coverage(coverage):
    with pytest.raises(ConfidenceServiceError):
        ConfidenceAssessment(
            confidence_score=0.5,
            confidence_level=ConfidenceLevel.MEDIUM,
            evidence_coverage=coverage,
            total_references=2,
            supported_references=1,
            unsupported_references=1,
            reasons=("Test reason.",),
        )


def test_assessment_rejects_invalid_reference_counts():
    with pytest.raises(ConfidenceServiceError):
        ConfidenceAssessment(
            confidence_score=0.5,
            confidence_level=ConfidenceLevel.MEDIUM,
            evidence_coverage=0.5,
            total_references=-1,
            supported_references=0,
            unsupported_references=0,
            reasons=("Test reason.",),
        )


def test_assessment_rejects_inconsistent_reference_counts():
    with pytest.raises(ConfidenceServiceError):
        ConfidenceAssessment(
            confidence_score=0.5,
            confidence_level=ConfidenceLevel.MEDIUM,
            evidence_coverage=0.5,
            total_references=3,
            supported_references=1,
            unsupported_references=1,
            reasons=("Test reason.",),
        )


def test_assessment_rejects_invalid_reasons():
    with pytest.raises(ConfidenceServiceError):
        ConfidenceAssessment(
            confidence_score=0.5,
            confidence_level=ConfidenceLevel.MEDIUM,
            evidence_coverage=0.5,
            total_references=2,
            supported_references=1,
            unsupported_references=1,
            reasons=("Valid reason.", ""),
        )


def test_medium_threshold_is_respected(service, response):
    result = service.assess(
        response,
        make_validation(
            supported_files=("app/main.py",),
            unsupported_files=("app/services/user_service.py",),
            supported_entities=(),
            unsupported_entities=("entity-1",),
        ),
    )

    assert result.confidence_score == pytest.approx(0.6667)
    assert result.confidence_level == ConfidenceLevel.MEDIUM


def test_result_contains_explanatory_reasons(service, response):
    result = service.assess(response, make_validation())

    assert result.reasons
    assert all(isinstance(reason, str) for reason in result.reasons)
