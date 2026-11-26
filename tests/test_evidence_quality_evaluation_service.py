import pytest

from appy.application.context_builder import (
    ContextBuildResult,
    ContextSection,
)
from appy.application.evidence_quality_evaluation_service import (
    EvidenceQualityEvaluationError,
    EvidenceQualityEvaluationResult,
    EvidenceQualityEvaluationService,
    EvidenceQualityLevel,
)
from appy.application.evidence_validation_agent import (
    EvidenceValidationResult,
)
from appy.application.intent_detection_service import QueryIntent
from appy.application.reasoning_response_model import ReasoningResponse


@pytest.fixture
def service():
    return EvidenceQualityEvaluationService()


@pytest.fixture
def response():
    return create_response()


@pytest.fixture
def context():
    return create_context()


@pytest.fixture
def validation_result():
    return create_validation_result()


def create_response(
    source_files=("appy/main.py",),
    entity_ids=("entity-1",),
    evidence_sufficient=True,
):
    return ReasoningResponse(
        question="Explain the application architecture",
        answer="The application uses a layered architecture.",
        intent=next(iter(QueryIntent)),
        source_files=source_files,
        entity_ids=entity_ids,
        provider_name="openai",
        model_name="gpt-test",
        evidence_sufficient=evidence_sufficient,
    )


def create_context(
    source_files=("appy/main.py", "appy/services/user.py"),
    entity_ids=("entity-1", "entity-2"),
    sections=None,
    context_text="Repository architecture context",
    truncated=False,
):
    if sections is None:
        sections = (
            ContextSection(
                name="repository",
                content="Repository structure and metadata.",
                source_files=("appy/main.py",),
            ),
            ContextSection(
                name="code",
                content="Relevant application code.",
                entity_ids=("entity-1",),
            ),
        )

    return ContextBuildResult(
        question="Explain the application architecture",
        intent="architecture",
        sections=sections,
        context_text=context_text,
        source_files=source_files,
        entity_ids=entity_ids,
        character_count=len(context_text),
        max_characters=12000,
        truncated=truncated,
    )


def create_validation_result(
    supported_source_files=("appy/main.py",),
    unsupported_source_files=(),
    supported_entity_ids=("entity-1",),
    unsupported_entity_ids=(),
    is_valid=True,
    evidence_sufficient=True,
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
    service=None,
    response=None,
    context=None,
    validation_result=None,
):
    evaluator = service or EvidenceQualityEvaluationService()

    return evaluator.evaluate(
        response=response or create_response(),
        context=context or create_context(),
        validation_result=(
            validation_result or create_validation_result()
        ),
    )


# ---------------------------------------------------------
# Basic evaluation
# ---------------------------------------------------------


def test_evaluate_returns_evidence_quality_result():
    result = evaluate()

    assert isinstance(result, EvidenceQualityEvaluationResult)


def test_evaluate_returns_valid_quality_level():
    result = evaluate()

    assert isinstance(result.quality_level, EvidenceQualityLevel)


def test_evaluate_returns_score_between_zero_and_one_hundred():
    result = evaluate()

    assert 0.0 <= result.overall_score <= 100.0


def test_evaluate_returns_all_dimension_scores():
    result = evaluate()

    assert 0.0 <= result.reference_support_score <= 100.0
    assert 0.0 <= result.source_coverage_score <= 100.0
    assert 0.0 <= result.entity_coverage_score <= 100.0
    assert 0.0 <= result.context_completeness_score <= 100.0
    assert 0.0 <= result.evidence_sufficiency_score <= 100.0


def test_evaluate_counts_supported_references():
    result = evaluate()

    assert result.supported_reference_count == 2


def test_evaluate_counts_unsupported_references():
    validation = create_validation_result(
        unsupported_source_files=("appy/missing.py",),
        unsupported_entity_ids=("entity-missing",),
        is_valid=False,
        issues=("Unsupported references detected.",),
    )

    result = evaluate(validation_result=validation)

    assert result.unsupported_reference_count == 2


def test_evaluate_counts_total_references():
    validation = create_validation_result(
        supported_source_files=("appy/main.py",),
        unsupported_source_files=("appy/missing.py",),
        supported_entity_ids=("entity-1",),
        unsupported_entity_ids=("entity-missing",),
        is_valid=False,
    )

    result = evaluate(validation_result=validation)

    assert result.total_reference_count == 4


def test_reference_counts_add_up_correctly():
    result = evaluate()

    assert (
        result.supported_reference_count
        + result.unsupported_reference_count
        == result.total_reference_count
    )


# ---------------------------------------------------------
# Reference support
# ---------------------------------------------------------


def test_reference_support_score_is_one_hundred_when_all_supported():
    validation = create_validation_result(
        supported_source_files=("appy/main.py",),
        supported_entity_ids=("entity-1",),
    )

    result = evaluate(validation_result=validation)

    assert result.reference_support_score == 100.0


def test_reference_support_score_handles_unsupported_references():
    validation = create_validation_result(
        supported_source_files=("appy/main.py",),
        unsupported_source_files=("appy/missing.py",),
        supported_entity_ids=("entity-1",),
        is_valid=False,
    )

    result = evaluate(validation_result=validation)

    assert result.reference_support_score == 66.67


def test_reference_support_score_is_zero_without_references():
    response = create_response(
        source_files=(),
        entity_ids=(),
    )
    validation = create_validation_result(
        supported_source_files=(),
        supported_entity_ids=(),
    )

    result = evaluate(
        response=response,
        validation_result=validation,
    )

    assert result.reference_support_score == 0.0


def test_unsupported_references_are_reported():
    validation = create_validation_result(
        unsupported_source_files=("appy/missing.py",),
        is_valid=False,
        issues=("Unsupported source file.",),
    )

    result = evaluate(validation_result=validation)

    assert result.has_unsupported_references
    assert result.unsupported_reference_count == 1


# ---------------------------------------------------------
# Source and entity coverage
# ---------------------------------------------------------


def test_source_coverage_score_uses_context_source_files():
    validation = create_validation_result(
        supported_source_files=("appy/main.py",),
    )

    result = evaluate(validation_result=validation)

    assert result.source_coverage_score == 50.0


def test_source_coverage_score_is_one_hundred_when_all_sources_covered():
    context = create_context(
        source_files=("appy/main.py",),
    )
    validation = create_validation_result(
        supported_source_files=("appy/main.py",),
    )

    result = evaluate(
        context=context,
        validation_result=validation,
    )

    assert result.source_coverage_score == 100.0


def test_source_coverage_score_is_one_hundred_without_context_sources():
    context = create_context(source_files=())
    validation = create_validation_result(
        supported_source_files=(),
    )

    result = evaluate(
        context=context,
        validation_result=validation,
    )

    assert result.source_coverage_score == 100.0


def test_entity_coverage_score_uses_context_entities():
    validation = create_validation_result(
        supported_entity_ids=("entity-1",),
    )

    result = evaluate(validation_result=validation)

    assert result.entity_coverage_score == 50.0


def test_entity_coverage_score_is_one_hundred_when_all_entities_covered():
    context = create_context(
        entity_ids=("entity-1",),
    )
    validation = create_validation_result(
        supported_entity_ids=("entity-1",),
    )

    result = evaluate(
        context=context,
        validation_result=validation,
    )

    assert result.entity_coverage_score == 100.0


def test_entity_coverage_score_is_one_hundred_without_context_entities():
    context = create_context(entity_ids=())
    validation = create_validation_result(
        supported_entity_ids=(),
    )

    result = evaluate(
        context=context,
        validation_result=validation,
    )

    assert result.entity_coverage_score == 100.0


def test_coverage_scores_are_capped_at_one_hundred():
    context = create_context(
        source_files=("appy/main.py",),
        entity_ids=("entity-1",),
    )
    validation = create_validation_result(
        supported_source_files=("appy/main.py", "appy/extra.py"),
        supported_entity_ids=("entity-1", "entity-2"),
    )

    result = evaluate(
        context=context,
        validation_result=validation,
    )

    assert result.source_coverage_score == 100.0
    assert result.entity_coverage_score == 100.0


# ---------------------------------------------------------
# Context completeness
# ---------------------------------------------------------


def test_context_completeness_score_counts_populated_sections():
    result = evaluate()

    assert result.context_completeness_score == 100.0


def test_context_completeness_score_handles_empty_sections():
    context = create_context(
        sections=(
            ContextSection(name="empty", content=""),
            ContextSection(name="populated", content="Useful context."),
        ),
    )

    result = evaluate(context=context)

    assert result.context_completeness_score == 50.0


def test_context_completeness_score_is_zero_when_all_sections_are_empty():
    context = create_context(
        sections=(
            ContextSection(name="first", content=""),
            ContextSection(name="second", content=""),
        ),
    )

    result = evaluate(context=context)

    assert result.context_completeness_score == 0.0


def test_context_completeness_score_handles_no_sections_with_text():
    context = create_context(
        sections=(),
        context_text="Available repository context.",
    )

    result = evaluate(context=context)

    assert result.context_completeness_score == 50.0


def test_context_completeness_score_is_zero_without_sections_or_text():
    context = create_context(
        sections=(),
        context_text="",
    )

    result = evaluate(context=context)

    assert result.context_completeness_score == 0.0


def test_context_section_counts_are_reported():
    result = evaluate()

    assert result.total_section_count == 2
    assert result.populated_section_count == 2


# ---------------------------------------------------------
# Evidence sufficiency and truncation
# ---------------------------------------------------------


def test_evidence_sufficiency_score_is_one_hundred_when_sufficient():
    result = evaluate()

    assert result.evidence_sufficiency_score == 100.0
    assert result.evidence_sufficient is True


def test_evidence_sufficiency_score_is_zero_when_response_is_insufficient():
    response = create_response(evidence_sufficient=False)

    result = evaluate(response=response)

    assert result.evidence_sufficiency_score == 0.0
    assert result.evidence_sufficient is False


def test_evidence_sufficiency_score_is_zero_when_validation_is_insufficient():
    validation = create_validation_result(
        evidence_sufficient=False,
    )

    result = evaluate(validation_result=validation)

    assert result.evidence_sufficiency_score == 0.0
    assert result.evidence_sufficient is False


def test_evidence_is_insufficient_when_either_input_reports_insufficient():
    response = create_response(evidence_sufficient=True)
    validation = create_validation_result(
        evidence_sufficient=False,
    )

    result = evaluate(
        response=response,
        validation_result=validation,
    )

    assert result.evidence_sufficient is False
    assert result.quality_level == EvidenceQualityLevel.INSUFFICIENT


def test_context_truncation_is_reported():
    context = create_context(truncated=True)

    result = evaluate(context=context)

    assert result.context_truncated is True
    assert any(
        "truncated" in finding.lower()
        for finding in result.findings
    )


# ---------------------------------------------------------
# Quality classification and findings
# ---------------------------------------------------------


def test_high_score_is_classified_as_high():
    level = EvidenceQualityEvaluationService._determine_quality_level(
        90.0,
        True,
    )

    assert level == EvidenceQualityLevel.HIGH


def test_medium_score_is_classified_as_medium():
    level = EvidenceQualityEvaluationService._determine_quality_level(
        75.0,
        True,
    )

    assert level == EvidenceQualityLevel.MEDIUM


def test_low_score_is_classified_as_low():
    level = EvidenceQualityEvaluationService._determine_quality_level(
        50.0,
        True,
    )

    assert level == EvidenceQualityLevel.LOW


def test_insufficient_evidence_overrides_score_classification():
    level = EvidenceQualityEvaluationService._determine_quality_level(
        95.0,
        False,
    )

    assert level == EvidenceQualityLevel.INSUFFICIENT


def test_findings_are_returned_as_tuple():
    result = evaluate()

    assert isinstance(result.findings, tuple)
    assert result.findings


def test_unsupported_validation_adds_finding():
    validation = create_validation_result(
        unsupported_source_files=("appy/missing.py",),
        is_valid=False,
        issues=("Unsupported source file.",),
    )

    result = evaluate(validation_result=validation)

    assert any(
        "unsupported" in finding.lower()
        for finding in result.findings
    )


def test_missing_answer_references_adds_finding():
    response = create_response(
        source_files=(),
        entity_ids=(),
    )
    validation = create_validation_result(
        supported_source_files=(),
        supported_entity_ids=(),
    )

    result = evaluate(
        response=response,
        validation_result=validation,
    )

    assert any(
        "does not contain" in finding.lower()
        for finding in result.findings
    )


def test_result_reports_context_reference_counts():
    result = evaluate()

    assert result.context_source_file_count == 2
    assert result.context_entity_count == 2


def test_is_reliable_requires_sufficient_supported_evidence():
    result = evaluate()

    assert result.is_reliable is True


def test_is_reliable_is_false_with_unsupported_references():
    validation = create_validation_result(
        supported_source_files=("appy/main.py",),
        unsupported_source_files=("appy/missing.py",),
        supported_entity_ids=("entity-1",),
        is_valid=False,
    )

    result = evaluate(validation_result=validation)

    assert result.is_reliable is False


def test_has_evidence_issues_for_low_quality():
    context = create_context(
        sections=(),
        context_text="",
        source_files=(),
        entity_ids=(),
    )
    response = create_response(
        source_files=(),
        entity_ids=(),
        evidence_sufficient=False,
    )
    validation = create_validation_result(
        supported_source_files=(),
        supported_entity_ids=(),
        evidence_sufficient=False,
    )

    result = evaluate(
        response=response,
        context=context,
        validation_result=validation,
    )

    assert result.has_evidence_issues is True


# ---------------------------------------------------------
# Input validation
# ---------------------------------------------------------


def test_response_must_be_reasoning_response():
    with pytest.raises(
        EvidenceQualityEvaluationError,
        match="response must be a ReasoningResponse",
    ):
        evaluate(response="invalid")


def test_context_must_be_context_build_result():
    with pytest.raises(
        EvidenceQualityEvaluationError,
        match="context must be a ContextBuildResult",
    ):
        evaluate(context="invalid")


def test_validation_result_must_be_correct_type():
    with pytest.raises(
        EvidenceQualityEvaluationError,
        match="validation_result must be an EvidenceValidationResult",
    ):
        evaluate(validation_result="invalid")


def test_result_rejects_score_above_one_hundred():
    with pytest.raises(EvidenceQualityEvaluationError):
        EvidenceQualityEvaluationResult(
            overall_score=101.0,
            quality_level=EvidenceQualityLevel.HIGH,
            reference_support_score=100.0,
            source_coverage_score=100.0,
            entity_coverage_score=100.0,
            context_completeness_score=100.0,
            evidence_sufficiency_score=100.0,
            supported_reference_count=1,
            unsupported_reference_count=0,
            total_reference_count=1,
            context_source_file_count=1,
            context_entity_count=1,
            populated_section_count=1,
            total_section_count=1,
            evidence_sufficient=True,
            context_truncated=False,
            findings=(),
        )


def test_result_rejects_invalid_quality_level():
    with pytest.raises(EvidenceQualityEvaluationError):
        EvidenceQualityEvaluationResult(
            overall_score=90.0,
            quality_level="high",
            reference_support_score=100.0,
            source_coverage_score=100.0,
            entity_coverage_score=100.0,
            context_completeness_score=100.0,
            evidence_sufficiency_score=100.0,
            supported_reference_count=1,
            unsupported_reference_count=0,
            total_reference_count=1,
            context_source_file_count=1,
            context_entity_count=1,
            populated_section_count=1,
            total_section_count=1,
            evidence_sufficient=True,
            context_truncated=False,
            findings=(),
        )


def test_result_rejects_negative_counts():
    with pytest.raises(EvidenceQualityEvaluationError):
        EvidenceQualityEvaluationResult(
            overall_score=90.0,
            quality_level=EvidenceQualityLevel.HIGH,
            reference_support_score=100.0,
            source_coverage_score=100.0,
            entity_coverage_score=100.0,
            context_completeness_score=100.0,
            evidence_sufficiency_score=100.0,
            supported_reference_count=-1,
            unsupported_reference_count=0,
            total_reference_count=0,
            context_source_file_count=1,
            context_entity_count=1,
            populated_section_count=1,
            total_section_count=1,
            evidence_sufficient=True,
            context_truncated=False,
            findings=(),
        )


def test_result_rejects_inconsistent_reference_counts():
    with pytest.raises(
        EvidenceQualityEvaluationError,
        match="Reference counts must add up",
    ):
        EvidenceQualityEvaluationResult(
            overall_score=90.0,
            quality_level=EvidenceQualityLevel.HIGH,
            reference_support_score=100.0,
            source_coverage_score=100.0,
            entity_coverage_score=100.0,
            context_completeness_score=100.0,
            evidence_sufficiency_score=100.0,
            supported_reference_count=2,
            unsupported_reference_count=1,
            total_reference_count=2,
            context_source_file_count=1,
            context_entity_count=1,
            populated_section_count=1,
            total_section_count=1,
            evidence_sufficient=True,
            context_truncated=False,
            findings=(),
        )


def test_result_rejects_non_tuple_findings():
    with pytest.raises(
        EvidenceQualityEvaluationError,
        match="findings must be a tuple",
    ):
        EvidenceQualityEvaluationResult(
            overall_score=90.0,
            quality_level=EvidenceQualityLevel.HIGH,
            reference_support_score=100.0,
            source_coverage_score=100.0,
            entity_coverage_score=100.0,
            context_completeness_score=100.0,
            evidence_sufficiency_score=100.0,
            supported_reference_count=1,
            unsupported_reference_count=0,
            total_reference_count=1,
            context_source_file_count=1,
            context_entity_count=1,
            populated_section_count=1,
            total_section_count=1,
            evidence_sufficient=True,
            context_truncated=False,
            findings=["Invalid findings collection"],
        )