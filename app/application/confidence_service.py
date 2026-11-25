
"""Assess confidence in AI-generated repository answers."""

from dataclasses import dataclass
from enum import Enum

from app.application.evidence_validation_agent import (
    EvidenceValidationResult,
)
from app.application.reasoning_response_model import ReasoningResponse


class ConfidenceServiceError(ValueError):
    """Raised when confidence assessment input is invalid."""


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ConfidenceAssessment:
    """Confidence assessment for a repository question answer."""

    confidence_score: float
    confidence_level: ConfidenceLevel
    evidence_coverage: float
    total_references: int
    supported_references: int
    unsupported_references: int
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.confidence_score, bool)
            or not isinstance(self.confidence_score, (int, float))
            or not 0.0 <= self.confidence_score <= 1.0
        ):
            raise ConfidenceServiceError(
                "confidence_score must be between 0 and 1"
            )

        if not isinstance(self.confidence_level, ConfidenceLevel):
            raise ConfidenceServiceError(
                "confidence_level must be a ConfidenceLevel"
            )

        if (
            isinstance(self.evidence_coverage, bool)
            or not isinstance(self.evidence_coverage, (int, float))
            or not 0.0 <= self.evidence_coverage <= 1.0
        ):
            raise ConfidenceServiceError(
                "evidence_coverage must be between 0 and 1"
            )

        for field_name in (
            "total_references",
            "supported_references",
            "unsupported_references",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ConfidenceServiceError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            self.supported_references + self.unsupported_references
            != self.total_references
        ):
            raise ConfidenceServiceError(
                "Reference counts must add up to total_references"
            )

        if not isinstance(self.reasons, tuple) or not all(
            isinstance(reason, str) and reason.strip()
            for reason in self.reasons
        ):
            raise ConfidenceServiceError(
                "reasons must be a tuple of non-empty strings"
            )


class ConfidenceService:
    """Calculate evidence-based confidence for a reasoning response.

    The score measures evidence availability and reference validation.
    It does not establish whether the answer is semantically correct.
    """

    HIGH_THRESHOLD = 0.80
    MEDIUM_THRESHOLD = 0.50

    def assess(
        self,
        response: ReasoningResponse,
        validation_result: EvidenceValidationResult,
    ) -> ConfidenceAssessment:
        """Assess confidence using a response and its validation result."""

        self._validate_inputs(response, validation_result)

        supported_count = (
            len(validation_result.supported_source_files)
            + len(validation_result.supported_entity_ids)
        )
        unsupported_count = (
            len(validation_result.unsupported_source_files)
            + len(validation_result.unsupported_entity_ids)
        )
        total_count = supported_count + unsupported_count

        coverage = (
            supported_count / total_count
            if total_count
            else 0.0
        )

        reasons: list[str] = []

        if total_count:
            score = 0.5 + (0.5 * coverage)
            reasons.append(
                f"{supported_count} of {total_count} references "
                "are supported by the retrieved context."
            )
        else:
            score = 0.0
            reasons.append(
                "The answer does not contain source-file or entity references."
            )

        if not response.evidence_sufficient:
            score = min(score, 0.49)
            reasons.append(
                "The reasoning response indicates that evidence is insufficient."
            )
        else:
            reasons.append(
                "The reasoning response indicates that evidence is sufficient."
            )

        if not validation_result.evidence_sufficient:
            score = min(score, 0.49)
            reasons.append(
                "The evidence validation result indicates insufficient evidence."
            )

        if not validation_result.is_valid:
            score = min(score, 0.39)
            reasons.append(
                "Evidence validation failed; confidence is limited."
            )

        if unsupported_count:
            reasons.append(
                f"{unsupported_count} reference(s) were not found in the "
                "retrieved context."
            )

        for issue in validation_result.issues:
            if issue not in reasons:
                reasons.append(issue)

        score = round(max(0.0, min(1.0, score)), 4)

        if score >= self.HIGH_THRESHOLD:
            level = ConfidenceLevel.HIGH
        elif score >= self.MEDIUM_THRESHOLD:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        return ConfidenceAssessment(
            confidence_score=score,
            confidence_level=level,
            evidence_coverage=round(coverage, 4),
            total_references=total_count,
            supported_references=supported_count,
            unsupported_references=unsupported_count,
            reasons=tuple(reasons),
        )

    @staticmethod
    def _validate_inputs(
        response: ReasoningResponse,
        validation_result: EvidenceValidationResult,
    ) -> None:
        if not isinstance(response, ReasoningResponse):
            raise ConfidenceServiceError(
                "response must be a ReasoningResponse"
            )

        if not isinstance(validation_result, EvidenceValidationResult):
            raise ConfidenceServiceError(
                "validation_result must be an EvidenceValidationResult"
            )
