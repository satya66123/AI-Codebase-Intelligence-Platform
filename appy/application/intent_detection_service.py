
"""Detect the intent behind a user's codebase question."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Pattern

from appy.application.question_validation_service import (
    QuestionValidationError,
    QuestionValidationService,
    ValidatedQuestion,
)


class IntentDetectionError(ValueError):
    """Raised when intent detection receives invalid input."""


class QueryIntent(str, Enum):
    """Supported user question intents."""

    ARCHITECTURE = "architecture"
    FILE_LOCATION = "file_location"
    CODE_EXPLANATION = "code_explanation"
    DEPENDENCY = "dependency"
    CALL_RELATIONSHIP = "call_relationship"
    DATA_FLOW = "data_flow"
    EXECUTION_FLOW = "execution_flow"
    CHANGE_IMPACT = "change_impact"
    CONFIGURATION = "configuration"
    GENERAL_CODEBASE = "general_codebase"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentDetectionResult:
    """Result produced by the intent detection service."""

    question: str
    intent: QueryIntent
    confidence: float
    matched_terms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise IntentDetectionError(
                "Question must be a non-empty string."
            )

        if not isinstance(self.intent, QueryIntent):
            raise IntentDetectionError("Invalid query intent.")

        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise IntentDetectionError(
                "Confidence must be between 0.0 and 1.0."
            )

        if not isinstance(self.matched_terms, tuple):
            raise IntentDetectionError(
                "Matched terms must be a tuple."
            )

        if any(
            not isinstance(term, str) or not term.strip()
            for term in self.matched_terms
        ):
            raise IntentDetectionError(
                "Matched terms must contain non-empty strings."
            )


class IntentDetectionService:
    """Classify repository questions using deterministic rules."""

    _INTENT_PATTERNS: tuple[
        tuple[QueryIntent, tuple[str, ...]], ...
    ] = (
        (
            QueryIntent.CHANGE_IMPACT,
            (
                r"\bwhat happens if\b",
                r"\bimpact of\b",
                r"\bchange impact\b",
                r"\bif i modify\b",
                r"\bif i change\b",
                r"\baffected files\b",
                r"\baffect(?:s|ed)?\b",
                r"\bbreak(?:s)? if\b",
            ),
        ),
        (
            QueryIntent.CALL_RELATIONSHIP,
            (
                r"\bwhat calls\b",
                r"\bwho calls\b",
                r"\bcalled by\b",
                r"\bcallers?\b",
                r"\bfunction calls\b",
                r"\bcalling functions\b",
            ),
        ),
        (
            QueryIntent.DEPENDENCY,
            (
                r"\bdepend(?:s|ency|encies|ent)?\b",
                r"\bdependencies\b",
                r"\bimport(?:s|ed)?\b",
                r"\buses this module\b",
                r"\bused by\b",
                r"\bdependent files\b",
            ),
        ),
        (
            QueryIntent.DATA_FLOW,
            (
                r"\bdata flow\b",
                r"\bflow of data\b",
                r"\bhow does data\b",
                r"\bdata moves\b",
                r"\btrace the data\b",
            ),
        ),
        (
            QueryIntent.EXECUTION_FLOW,
            (
                r"\bexecution flow\b",
                r"\bexecution path\b",
                r"\bprogram flow\b",
                r"\bruntime flow\b",
                r"\bhow does .* execute\b",
                r"\bwhat happens when .* runs\b",
            ),
        ),
        (
            QueryIntent.CONFIGURATION,
            (
                r"\bconfiguration\b",
                r"\bconfig file\b",
                r"\benvironment variable\b",
                r"\bsettings\b",
                r"\bwhere is .* configured\b",
                r"\bconfiguration used\b",
            ),
        ),
        (
            QueryIntent.ARCHITECTURE,
            (
                r"\barchitecture\b",
                r"\barchitectural design\b",
                r"\bproject structure\b",
                r"\bsystem design\b",
                r"\bhigh[- ]level design\b",
                r"\bmain components\b",
                r"\bmodules of (?:the )?(?:project|repository|application)\b",
            ),
        ),
        (
            QueryIntent.FILE_LOCATION,
            (
                r"\bwhere is\b",
                r"\bwhere are\b",
                r"\bwhich file\b",
                r"\bwhich files\b",
                r"\blocation of\b",
                r"\bfind the file\b",
                r"\bimplemented\b",
                r"\bdefined\b",
            ),
        ),
        (
            QueryIntent.CODE_EXPLANATION,
            (
                r"\bexplain\b",
                r"\bhow does\b",
                r"\bhow do\b",
                r"\bwhat does\b",
                r"\bwhat is the purpose\b",
                r"\bdescribe\b",
                r"\bsummarize\b",
                r"\bsummary of\b",
            ),
        ),
    )

    _GENERAL_PATTERNS: tuple[str, ...] = (
        r"\boverview\b",
        r"\babout this repository\b",
        r"\babout this project\b",
        r"\bthis codebase\b",
        r"\brepository summary\b",
        r"\bproject summary\b",
        r"\bwhat is this project\b",
        r"\bwhat does this project contain\b",
        r"\bwhat does this repository contain\b",
    )

    def __init__(
        self,
        question_validator: QuestionValidationService | None = None,
    ) -> None:
        self.question_validator = (
            question_validator or QuestionValidationService()
        )

        if not isinstance(
            self.question_validator,
            QuestionValidationService,
        ):
            raise IntentDetectionError(
                "Question validator must be a QuestionValidationService."
            )

        self._compiled_patterns: tuple[
            tuple[QueryIntent, tuple[tuple[str, Pattern[str]], ...]],
            ...
        ] = tuple(
            (
                intent,
                tuple(
                    (pattern, re.compile(pattern, re.IGNORECASE))
                    for pattern in patterns
                ),
            )
            for intent, patterns in self._INTENT_PATTERNS
        )

        self._compiled_general_patterns = tuple(
            (pattern, re.compile(pattern, re.IGNORECASE))
            for pattern in self._GENERAL_PATTERNS
        )

    def detect(
        self,
        question: str | ValidatedQuestion,
    ) -> IntentDetectionResult:
        """
        Detect the primary intent of a repository question.

        Accepts either a raw string or a ValidatedQuestion.
        Raw strings are validated before classification.
        """
        if isinstance(question, ValidatedQuestion):
            normalized_question = question.question
        else:
            try:
                validated = self.question_validator.validate(question)
            except QuestionValidationError as exc:
                raise IntentDetectionError(str(exc)) from exc

            normalized_question = validated.question

        # General repository questions are checked first.
        general_matches = tuple(
            pattern
            for pattern, compiled in self._compiled_general_patterns
            if compiled.search(normalized_question)
        )

        if general_matches:
            return IntentDetectionResult(
                question=normalized_question,
                intent=QueryIntent.GENERAL_CODEBASE,
                confidence=0.80,
                matched_terms=general_matches,
            )

        # Check specialized intents next.
        for intent, patterns in self._compiled_patterns:
            matched_terms = tuple(
                pattern
                for pattern, compiled in patterns
                if compiled.search(normalized_question)
            )

            if matched_terms:
                return IntentDetectionResult(
                    question=normalized_question,
                    intent=intent,
                    confidence=0.90,
                    matched_terms=matched_terms,
                )

        return IntentDetectionResult(
            question=normalized_question,
            intent=QueryIntent.UNKNOWN,
            confidence=0.0,
            matched_terms=(),
        )
