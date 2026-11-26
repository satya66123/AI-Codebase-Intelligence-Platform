from dataclasses import dataclass
from enum import Enum

from appy.application.context_builder import ContextBuildResult
from appy.application.evidence_validation_agent import (
    EvidenceValidationResult,
)
from appy.application.reasoning_response_model import ReasoningResponse


class EvidenceQualityEvaluationError(ValueError):
    """Raised when evidence quality evaluation receives invalid input."""


class EvidenceQualityLevel(str, Enum):
    """Overall evidence quality classification."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class EvidenceQualityEvaluationResult:
    """Contains the measured quality and coverage of answer evidence."""

    overall_score: float
    quality_level: EvidenceQualityLevel
    reference_support_score: float
    source_coverage_score: float
    entity_coverage_score: float
    context_completeness_score: float
    evidence_sufficiency_score: float
    supported_reference_count: int
    unsupported_reference_count: int
    total_reference_count: int
    context_source_file_count: int
    context_entity_count: int
    populated_section_count: int
    total_section_count: int
    evidence_sufficient: bool
    context_truncated: bool
    findings: tuple[str, ...]

    def __post_init__(self):
        score_fields = (
            "overall_score",
            "reference_support_score",
            "source_coverage_score",
            "entity_coverage_score",
            "context_completeness_score",
            "evidence_sufficiency_score",
        )

        for field_name in score_fields:
            value = getattr(self, field_name)

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0.0 <= value <= 100.0
            ):
                raise EvidenceQualityEvaluationError(
                    f"{field_name} must be between 0 and 100."
                )

        if not isinstance(self.quality_level, EvidenceQualityLevel):
            raise EvidenceQualityEvaluationError(
                "quality_level must be an EvidenceQualityLevel."
            )

        count_fields = (
            "supported_reference_count",
            "unsupported_reference_count",
            "total_reference_count",
            "context_source_file_count",
            "context_entity_count",
            "populated_section_count",
            "total_section_count",
        )

        for field_name in count_fields:
            value = getattr(self, field_name)

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise EvidenceQualityEvaluationError(
                    f"{field_name} must be a non-negative integer."
                )

        if (
            self.supported_reference_count
            + self.unsupported_reference_count
            != self.total_reference_count
        ):
            raise EvidenceQualityEvaluationError(
                "Reference counts must add up to total_reference_count."
            )

        if self.populated_section_count > self.total_section_count:
            raise EvidenceQualityEvaluationError(
                "Populated sections cannot exceed total sections."
            )

        if not isinstance(self.evidence_sufficient, bool):
            raise EvidenceQualityEvaluationError(
                "evidence_sufficient must be a boolean."
            )

        if not isinstance(self.context_truncated, bool):
            raise EvidenceQualityEvaluationError(
                "context_truncated must be a boolean."
            )

        if not isinstance(self.findings, tuple):
            raise EvidenceQualityEvaluationError(
                "findings must be a tuple."
            )

        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.findings
        ):
            raise EvidenceQualityEvaluationError(
                "findings must contain non-empty strings."
            )

    @property
    def has_evidence_issues(self) -> bool:
        """Return whether the assessment identified evidence concerns."""

        return self.quality_level in (
            EvidenceQualityLevel.LOW,
            EvidenceQualityLevel.INSUFFICIENT,
        )

    @property
    def is_reliable(self) -> bool:
        """Return whether the evidence meets the reliability threshold."""

        return (
            self.overall_score >= 70.0
            and self.evidence_sufficient
            and self.unsupported_reference_count == 0
        )

    @property
    def has_unsupported_references(self) -> bool:
        return self.unsupported_reference_count > 0


class EvidenceQualityEvaluationService:
    """
    Evaluates evidence quality using retrieved context and reference validation.

    This service measures evidence availability, reference support, coverage,
    and context completeness. It does not prove semantic correctness.
    """

    REFERENCE_SUPPORT_WEIGHT = 0.35
    SOURCE_COVERAGE_WEIGHT = 0.20
    ENTITY_COVERAGE_WEIGHT = 0.15
    CONTEXT_COMPLETENESS_WEIGHT = 0.15
    SUFFICIENCY_WEIGHT = 0.15

    HIGH_THRESHOLD = 85.0
    MEDIUM_THRESHOLD = 70.0
    LOW_THRESHOLD = 40.0

    def evaluate(
        self,
        response: ReasoningResponse,
        context: ContextBuildResult,
        validation_result: EvidenceValidationResult,
    ) -> EvidenceQualityEvaluationResult:
        """Evaluate the evidence supporting a reasoning response."""

        self._validate_inputs(
            response,
            context,
            validation_result,
        )

        supported_reference_count = (
            len(validation_result.supported_source_files)
            + len(validation_result.supported_entity_ids)
        )

        unsupported_reference_count = (
            len(validation_result.unsupported_source_files)
            + len(validation_result.unsupported_entity_ids)
        )

        total_reference_count = (
            supported_reference_count
            + unsupported_reference_count
        )

        reference_support_score = self._reference_support_score(
            supported_reference_count,
            total_reference_count,
        )

        source_coverage_score = self._coverage_score(
            len(validation_result.supported_source_files),
            len(context.source_files),
        )

        entity_coverage_score = self._coverage_score(
            len(validation_result.supported_entity_ids),
            len(context.entity_ids),
        )

        populated_section_count = sum(
            1
            for section in context.sections
            if section.content.strip()
        )

        context_completeness_score = self._context_completeness_score(
            context,
            populated_section_count,
        )

        evidence_sufficient = (
            response.evidence_sufficient
            and validation_result.evidence_sufficient
        )

        evidence_sufficiency_score = (
            100.0 if evidence_sufficient else 0.0
        )

        overall_score = self._calculate_overall_score(
            reference_support_score,
            source_coverage_score,
            entity_coverage_score,
            context_completeness_score,
            evidence_sufficiency_score,
        )

        findings = self._build_findings(
            response,
            context,
            validation_result,
            supported_reference_count,
            unsupported_reference_count,
            total_reference_count,
            populated_section_count,
            evidence_sufficient,
        )

        quality_level = self._determine_quality_level(
            overall_score,
            evidence_sufficient,
        )

        return EvidenceQualityEvaluationResult(
            overall_score=overall_score,
            quality_level=quality_level,
            reference_support_score=reference_support_score,
            source_coverage_score=source_coverage_score,
            entity_coverage_score=entity_coverage_score,
            context_completeness_score=context_completeness_score,
            evidence_sufficiency_score=evidence_sufficiency_score,
            supported_reference_count=supported_reference_count,
            unsupported_reference_count=unsupported_reference_count,
            total_reference_count=total_reference_count,
            context_source_file_count=len(context.source_files),
            context_entity_count=len(context.entity_ids),
            populated_section_count=populated_section_count,
            total_section_count=len(context.sections),
            evidence_sufficient=evidence_sufficient,
            context_truncated=context.truncated,
            findings=findings,
        )

    @staticmethod
    def _reference_support_score(
        supported_count: int,
        total_count: int,
    ) -> float:
        if total_count == 0:
            return 0.0

        return round(
            supported_count / total_count * 100.0,
            2,
        )

    @staticmethod
    def _coverage_score(
        supported_count: int,
        context_count: int,
    ) -> float:
        if context_count == 0:
            return 100.0

        return round(
            min(supported_count / context_count, 1.0) * 100.0,
            2,
        )

    @staticmethod
    def _context_completeness_score(
        context: ContextBuildResult,
        populated_section_count: int,
    ) -> float:
        if context.sections:
            return round(
                populated_section_count / len(context.sections) * 100.0,
                2,
            )

        if context.context_text.strip():
            return 50.0

        return 0.0

    def _calculate_overall_score(
        self,
        reference_support_score: float,
        source_coverage_score: float,
        entity_coverage_score: float,
        context_completeness_score: float,
        evidence_sufficiency_score: float,
    ) -> float:
        score = (
            reference_support_score * self.REFERENCE_SUPPORT_WEIGHT
            + source_coverage_score * self.SOURCE_COVERAGE_WEIGHT
            + entity_coverage_score * self.ENTITY_COVERAGE_WEIGHT
            + context_completeness_score * self.CONTEXT_COMPLETENESS_WEIGHT
            + evidence_sufficiency_score * self.SUFFICIENCY_WEIGHT
        )

        return round(max(0.0, min(score, 100.0)), 2)

    def _build_findings(
        self,
        response: ReasoningResponse,
        context: ContextBuildResult,
        validation_result: EvidenceValidationResult,
        supported_reference_count: int,
        unsupported_reference_count: int,
        total_reference_count: int,
        populated_section_count: int,
        evidence_sufficient: bool,
    ) -> tuple[str, ...]:
        findings = []

        if total_reference_count == 0:
            findings.append(
                "The answer does not contain source-file or entity references."
            )
        elif unsupported_reference_count:
            findings.append(
                f"{unsupported_reference_count} answer reference(s) "
                "are not supported by the retrieved context."
            )
        else:
            findings.append(
                f"All {supported_reference_count} answer reference(s) "
                "are supported by the retrieved context."
            )

        if not context.source_files:
            findings.append(
                "The retrieved context does not contain source-file references."
            )

        if not context.entity_ids:
            findings.append(
                "The retrieved context does not contain entity references."
            )

        if context.sections and populated_section_count == 0:
            findings.append(
                "All retrieved context sections are empty."
            )
        elif context.sections:
            findings.append(
                f"{populated_section_count} of {len(context.sections)} "
                "context section(s) contain content."
            )

        if not evidence_sufficient:
            findings.append(
                "The response or evidence validation indicates "
                "that the available evidence is insufficient."
            )

        if context.truncated:
            findings.append(
                "The retrieved context was truncated to fit its character limit."
            )

        if not validation_result.is_valid:
            findings.append(
                "Evidence validation identified unsupported references."
            )

        if validation_result.issues:
            findings.extend(validation_result.issues)

        if (
            response.evidence_sufficient
            and validation_result.evidence_sufficient
            and total_reference_count == 0
        ):
            findings.append(
                "Evidence sufficiency is declared, but no answer references "
                "are available for reference-based verification."
            )

        return self._unique_findings(findings)

    @staticmethod
    def _unique_findings(findings: list[str]) -> tuple[str, ...]:
        unique = []
        seen = set()

        for finding in findings:
            if finding not in seen:
                seen.add(finding)
                unique.append(finding)

        return tuple(unique)

    @classmethod
    def _determine_quality_level(
        cls,
        overall_score: float,
        evidence_sufficient: bool,
    ) -> EvidenceQualityLevel:
        if not evidence_sufficient:
            return EvidenceQualityLevel.INSUFFICIENT

        if overall_score >= cls.HIGH_THRESHOLD:
            return EvidenceQualityLevel.HIGH

        if overall_score >= cls.MEDIUM_THRESHOLD:
            return EvidenceQualityLevel.MEDIUM

        if overall_score >= cls.LOW_THRESHOLD:
            return EvidenceQualityLevel.LOW

        return EvidenceQualityLevel.INSUFFICIENT

    @staticmethod
    def _validate_inputs(
        response: ReasoningResponse,
        context: ContextBuildResult,
        validation_result: EvidenceValidationResult,
    ) -> None:
        if not isinstance(response, ReasoningResponse):
            raise EvidenceQualityEvaluationError(
                "response must be a ReasoningResponse instance."
            )

        if not isinstance(context, ContextBuildResult):
            raise EvidenceQualityEvaluationError(
                "context must be a ContextBuildResult instance."
            )

        if not isinstance(validation_result, EvidenceValidationResult):
            raise EvidenceQualityEvaluationError(
                "validation_result must be an EvidenceValidationResult instance."
            )

        if not isinstance(response.source_files, tuple):
            raise EvidenceQualityEvaluationError(
                "Response source_files must be a tuple."
            )

        if not isinstance(response.entity_ids, tuple):
            raise EvidenceQualityEvaluationError(
                "Response entity_ids must be a tuple."
            )

        if not isinstance(context.source_files, tuple):
            raise EvidenceQualityEvaluationError(
                "Context source_files must be a tuple."
            )

        if not isinstance(context.entity_ids, tuple):
            raise EvidenceQualityEvaluationError(
                "Context entity_ids must be a tuple."
            )

        if not isinstance(context.sections, tuple):
            raise EvidenceQualityEvaluationError(
                "Context sections must be a tuple."
            )

        if not isinstance(context.context_text, str):
            raise EvidenceQualityEvaluationError(
                "Context context_text must be a string."
            )

        if not isinstance(context.truncated, bool):
            raise EvidenceQualityEvaluationError(
                "Context truncated must be a boolean."
            )

        reference_fields = (
            "supported_source_files",
            "unsupported_source_files",
            "supported_entity_ids",
            "unsupported_entity_ids",
        )

        for field_name in reference_fields:
            value = getattr(validation_result, field_name)

            if not isinstance(value, tuple):
                raise EvidenceQualityEvaluationError(
                    f"Validation {field_name} must be a tuple."
                )

            if any(
                not isinstance(item, str) or not item.strip()
                for item in value
            ):
                raise EvidenceQualityEvaluationError(
                    f"Validation {field_name} must contain non-empty strings."
                )

        if not isinstance(validation_result.is_valid, bool):
            raise EvidenceQualityEvaluationError(
                "Validation is_valid must be a boolean."
            )

        if not isinstance(validation_result.evidence_sufficient, bool):
            raise EvidenceQualityEvaluationError(
                "Validation evidence_sufficient must be a boolean."
            )