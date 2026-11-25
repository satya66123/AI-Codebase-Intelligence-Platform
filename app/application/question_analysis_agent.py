
"""Coordinate question validation and intent detection."""

from dataclasses import dataclass

from app.application.question_validation_service import (
    QuestionValidationError,
    QuestionValidationService,
)
from app.application.intent_detection_service import (
    IntentDetectionError,
    IntentDetectionService,
    QueryIntent,
)


class QuestionAnalysisError(ValueError):
    """Raised when question analysis fails."""


@dataclass(frozen=True)
class QuestionAnalysisResult:
    """Structured analysis of a user's repository question."""

    question: str
    intent: QueryIntent
    confidence: float
    matched_terms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise QuestionAnalysisError(
                "Question must be a non-empty string."
            )

        if not isinstance(self.intent, QueryIntent):
            raise QuestionAnalysisError("Invalid question intent.")

        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise QuestionAnalysisError(
                "Confidence must be between 0.0 and 1.0."
            )

        if not isinstance(self.matched_terms, tuple):
            raise QuestionAnalysisError(
                "Matched terms must be a tuple."
            )

        if any(
            not isinstance(term, str) or not term.strip()
            for term in self.matched_terms
        ):
            raise QuestionAnalysisError(
                "Matched terms must contain non-empty strings."
            )


class QuestionAnalysisAgent:
    """
    Analyze user questions before repository intelligence retrieval.
    """

    def __init__(
        self,
        question_validator: QuestionValidationService | None = None,
        intent_detector: IntentDetectionService | None = None,
    ) -> None:

        # Validate dependencies before constructing dependent services.
        if question_validator is not None and not isinstance(
            question_validator,
            QuestionValidationService,
        ):
            raise QuestionAnalysisError(
                "Invalid question validation service."
            )

        if intent_detector is not None and not isinstance(
            intent_detector,
            IntentDetectionService,
        ):
            raise QuestionAnalysisError(
                "Invalid intent detection service."
            )

        self.question_validator = (
            question_validator or QuestionValidationService()
        )

        self.intent_detector = (
            intent_detector
            or IntentDetectionService(
                question_validator=self.question_validator
            )
        )

    def analyze(self, question: str) -> QuestionAnalysisResult:
        """Validate and analyze a user's repository question."""

        try:
            validated_question = self.question_validator.validate(
                question
            )

            intent_result = self.intent_detector.detect(
                validated_question
            )

            # Convert regex patterns into readable matched terms.
            readable_terms = tuple(
                term.strip(r"\b")
                for term in intent_result.matched_terms
            )

            return QuestionAnalysisResult(
                question=intent_result.question,
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                matched_terms=readable_terms,
            )

        except QuestionValidationError as exc:
            raise QuestionAnalysisError(
                f"Question validation failed: {exc}"
            ) from exc

        except IntentDetectionError as exc:
            raise QuestionAnalysisError(
                f"Intent detection failed: {exc}"
            ) from exc
