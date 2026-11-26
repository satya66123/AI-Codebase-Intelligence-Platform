
from dataclasses import dataclass
import re
from typing import Any

from app.application.context_builder import ContextBuildResult
from app.application.evidence_validation_agent import (
    EvidenceValidationResult,
)
from app.application.reasoning_response_model import ReasoningResponse


class AIAnswerQualityEvaluationError(ValueError):
    """Raised when AI answer quality evaluation fails."""


class AnswerQualityLevel:
    """Quality levels assigned to evaluated answers."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass(frozen=True)
class AnswerQualityDimension:
    """Contains the score and findings for one quality dimension."""

    name: str
    score: float
    weight: float
    findings: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise AIAnswerQualityEvaluationError(
                "Dimension name must be a non-empty string."
            )

        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not 0.0 <= self.score <= 100.0
        ):
            raise AIAnswerQualityEvaluationError(
                "Dimension score must be between 0 and 100."
            )

        if (
            isinstance(self.weight, bool)
            or not isinstance(self.weight, (int, float))
            or not 0.0 <= self.weight <= 1.0
        ):
            raise AIAnswerQualityEvaluationError(
                "Dimension weight must be between 0 and 1."
            )

        if not isinstance(self.findings, tuple):
            raise AIAnswerQualityEvaluationError(
                "Dimension findings must be a tuple."
            )

        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.findings
        ):
            raise AIAnswerQualityEvaluationError(
                "Dimension findings must contain non-empty strings."
            )


@dataclass(frozen=True)
class AIAnswerQualityEvaluationResult:
    """Contains the complete quality assessment for an AI answer."""

    question: str
    overall_score: float
    quality_level: str
    relevance: AnswerQualityDimension
    completeness: AnswerQualityDimension
    clarity: AnswerQualityDimension
    evidence_grounding: AnswerQualityDimension
    evidence_sufficient: bool
    unsupported_reference_count: int
    supported_reference_count: int
    total_reference_count: int
    findings: tuple[str, ...]

    @property
    def is_acceptable(self) -> bool:
        """Return whether the answer meets the minimum quality threshold."""
        return self.overall_score >= 60.0

    @property
    def has_evidence_issues(self) -> bool:
        """Return whether unsupported references or insufficient evidence exist."""
        return (
            self.unsupported_reference_count > 0
            or not self.evidence_sufficient
        )

    @property
    def dimensions(self) -> tuple[AnswerQualityDimension, ...]:
        """Return all evaluated quality dimensions."""
        return (
            self.relevance,
            self.completeness,
            self.clarity,
            self.evidence_grounding,
        )


class AIAnswerQualityEvaluationService:
    """
    Evaluate answer quality using deterministic, explainable heuristics.

    The service evaluates textual relevance, answer completeness,
    readability, and evidence-reference grounding.

    It does not claim to prove semantic correctness or detect every
    hallucinated statement.
    """

    DIMENSION_WEIGHTS = {
        "relevance": 0.30,
        "completeness": 0.20,
        "clarity": 0.20,
        "evidence_grounding": 0.30,
    }

    EXCELLENT_THRESHOLD = 85.0
    GOOD_THRESHOLD = 70.0
    FAIR_THRESHOLD = 50.0

    STOP_WORDS = frozenset({
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "could",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "or",
        "our",
        "please",
        "show",
        "tell",
        "that",
        "the",
        "their",
        "this",
        "to",
        "us",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    })

    def evaluate(
        self,
        response: ReasoningResponse,
        context: ContextBuildResult,
        evidence_result: EvidenceValidationResult,
    ) -> AIAnswerQualityEvaluationResult:
        """Evaluate one reasoning response against its retrieved context."""

        self._validate_inputs(
            response,
            context,
            evidence_result,
        )

        relevance = self._evaluate_relevance(response)
        completeness = self._evaluate_completeness(response)
        clarity = self._evaluate_clarity(response)
        evidence_grounding = self._evaluate_evidence(
            response,
            context,
            evidence_result,
        )

        dimensions = (
            relevance,
            completeness,
            clarity,
            evidence_grounding,
        )

        overall_score = round(
            sum(
                dimension.score * dimension.weight
                for dimension in dimensions
            ),
            2,
        )

        quality_level = self._determine_quality_level(
            overall_score
        )

        supported_reference_count = (
            len(evidence_result.supported_source_files)
            + len(evidence_result.supported_entity_ids)
        )

        unsupported_reference_count = (
            len(evidence_result.unsupported_source_files)
            + len(evidence_result.unsupported_entity_ids)
        )

        total_reference_count = (
            supported_reference_count
            + unsupported_reference_count
        )

        findings = tuple(
            finding
            for dimension in dimensions
            for finding in dimension.findings
        )

        return AIAnswerQualityEvaluationResult(
            question=response.question,
            overall_score=overall_score,
            quality_level=quality_level,
            relevance=relevance,
            completeness=completeness,
            clarity=clarity,
            evidence_grounding=evidence_grounding,
            evidence_sufficient=(
                evidence_result.evidence_sufficient
                and response.evidence_sufficient
            ),
            unsupported_reference_count=(
                unsupported_reference_count
            ),
            supported_reference_count=supported_reference_count,
            total_reference_count=total_reference_count,
            findings=findings,
        )

    @staticmethod
    def _validate_inputs(
        response: ReasoningResponse,
        context: ContextBuildResult,
        evidence_result: EvidenceValidationResult,
    ) -> None:
        """Validate all evaluation input models."""

        if not isinstance(response, ReasoningResponse):
            raise AIAnswerQualityEvaluationError(
                "response must be a ReasoningResponse instance."
            )

        if not isinstance(context, ContextBuildResult):
            raise AIAnswerQualityEvaluationError(
                "context must be a ContextBuildResult instance."
            )

        if not isinstance(evidence_result, EvidenceValidationResult):
            raise AIAnswerQualityEvaluationError(
                "evidence_result must be an EvidenceValidationResult instance."
            )

        if response.question.strip() == "":
            raise AIAnswerQualityEvaluationError(
                "Response question cannot be empty."
            )

        if response.answer.strip() == "":
            raise AIAnswerQualityEvaluationError(
                "Response answer cannot be empty."
            )

        if not isinstance(context.context_text, str):
            raise AIAnswerQualityEvaluationError(
                "Context text must be a string."
            )

        if not isinstance(response.source_files, tuple):
            raise AIAnswerQualityEvaluationError(
                "Response source_files must be a tuple."
            )

        if not isinstance(response.entity_ids, tuple):
            raise AIAnswerQualityEvaluationError(
                "Response entity_ids must be a tuple."
            )

        if not isinstance(context.source_files, tuple):
            raise AIAnswerQualityEvaluationError(
                "Context source_files must be a tuple."
            )

        if not isinstance(context.entity_ids, tuple):
            raise AIAnswerQualityEvaluationError(
                "Context entity_ids must be a tuple."
            )

        if not isinstance(evidence_result.issues, tuple):
            raise AIAnswerQualityEvaluationError(
                "Evidence issues must be a tuple."
            )

    @classmethod
    def _tokenize(cls, text: str) -> tuple[str, ...]:
        """Extract normalized meaningful tokens from text."""

        tokens = re.findall(
            r"[a-zA-Z_][a-zA-Z0-9_]*",
            text.casefold(),
        )

        return tuple(
            token
            for token in tokens
            if token not in cls.STOP_WORDS
            and len(token) > 1
        )

    @classmethod
    def _evaluate_relevance(
        cls,
        response: ReasoningResponse,
    ) -> AnswerQualityDimension:
        """Estimate question-answer relevance using token overlap."""

        question_tokens = set(
            cls._tokenize(response.question)
        )

        answer_tokens = set(
            cls._tokenize(response.answer)
        )

        if not question_tokens:
            score = 50.0
            findings = (
                "Question contains insufficient meaningful tokens "
                "for lexical relevance evaluation.",
            )
        else:
            overlap = question_tokens.intersection(answer_tokens)

            score = (
                len(overlap) / len(question_tokens)
            ) * 100.0

            findings_list = []

            if not overlap:
                findings_list.append(
                    "Answer does not share meaningful keywords "
                    "with the question."
                )
            elif score < 40.0:
                findings_list.append(
                    "Answer has limited keyword overlap with the question."
                )
            else:
                findings_list.append(
                    "Answer contains meaningful keywords from the question."
                )

            findings = tuple(findings_list)

        return AnswerQualityDimension(
            name="relevance",
            score=round(score, 2),
            weight=cls.DIMENSION_WEIGHTS["relevance"],
            findings=findings,
        )

    @classmethod
    def _evaluate_completeness(
        cls,
        response: ReasoningResponse,
    ) -> AnswerQualityDimension:
        """Estimate answer completeness using content structure."""

        answer = response.answer.strip()
        words = answer.split()
        word_count = len(words)

        sentences = cls._split_sentences(answer)
        sentence_count = len(sentences)

        if word_count < 5:
            score = 20.0
            findings = (
                "Answer is very short and may not provide enough detail.",
            )
        elif word_count < 15:
            score = 45.0
            findings = (
                "Answer contains limited detail.",
            )
        elif word_count < 30:
            score = 65.0
            findings = (
                "Answer provides some detail but may benefit from "
                "additional explanation.",
            )
        elif word_count < 60:
            score = 80.0
            findings = (
                "Answer provides a reasonable amount of detail.",
            )
        else:
            score = 95.0
            findings = (
                "Answer provides substantial textual detail.",
            )

        if sentence_count == 1 and word_count >= 30:
            score -= 5.0
            findings += (
                "Answer is a single long sentence; consider clearer structure.",
            )

        if not answer.endswith((".", "!", "?", ":", ")")):
            score -= 5.0
            findings += (
                "Answer does not end with conventional sentence punctuation.",
            )

        score = max(0.0, min(100.0, score))

        return AnswerQualityDimension(
            name="completeness",
            score=round(score, 2),
            weight=cls.DIMENSION_WEIGHTS["completeness"],
            findings=findings,
        )

    @classmethod
    def _evaluate_clarity(
        cls,
        response: ReasoningResponse,
    ) -> AnswerQualityDimension:
        """Estimate readability using sentence length and structure."""

        answer = response.answer.strip()
        sentences = cls._split_sentences(answer)
        words = answer.split()

        if not words:
            return AnswerQualityDimension(
                name="clarity",
                score=0.0,
                weight=cls.DIMENSION_WEIGHTS["clarity"],
                findings=("Answer contains no readable text.",),
            )

        if not sentences:
            average_sentence_length = len(words)
        else:
            average_sentence_length = (
                len(words) / len(sentences)
            )

        score = 100.0
        findings = []

        if average_sentence_length > 35:
            score -= 30.0
            findings.append(
                "Sentences are very long and may be difficult to follow."
            )
        elif average_sentence_length > 25:
            score -= 15.0
            findings.append(
                "Some sentences may benefit from shorter phrasing."
            )
        else:
            findings.append(
                "Sentence length is within a readable range."
            )

        if len(words) >= 20 and len(sentences) < 2:
            score -= 10.0
            findings.append(
                "Consider separating the answer into multiple sentences."
            )

        repeated_words = cls._find_repeated_words(words)

        if repeated_words:
            score -= min(20.0, len(repeated_words) * 5.0)
            findings.append(
                "Answer contains repeated words: "
                + ", ".join(repeated_words)
                + "."
            )

        if "\n\n" in answer:
            findings.append(
                "Answer uses paragraph breaks to organize information."
            )

        score = max(0.0, min(100.0, score))

        return AnswerQualityDimension(
            name="clarity",
            score=round(score, 2),
            weight=cls.DIMENSION_WEIGHTS["clarity"],
            findings=tuple(findings),
        )

    @classmethod
    def _evaluate_evidence(
        cls,
        response: ReasoningResponse,
        context: ContextBuildResult,
        evidence_result: EvidenceValidationResult,
    ) -> AnswerQualityDimension:
        """Evaluate evidence sufficiency and reference integrity."""

        supported_count = (
            len(evidence_result.supported_source_files)
            + len(evidence_result.supported_entity_ids)
        )

        unsupported_count = (
            len(evidence_result.unsupported_source_files)
            + len(evidence_result.unsupported_entity_ids)
        )

        total_count = supported_count + unsupported_count

        findings = []

        if not response.evidence_sufficient:
            findings.append(
                "The reasoning response indicates insufficient evidence."
            )

        if not evidence_result.evidence_sufficient:
            findings.append(
                "Evidence validation indicates insufficient evidence."
            )

        if not context.context_text.strip():
            findings.append(
                "Retrieved context contains no textual evidence."
            )

        if unsupported_count:
            findings.append(
                f"{unsupported_count} answer reference(s) are not "
                "supported by the retrieved context."
            )

        if not evidence_result.is_valid:
            findings.append(
                "Evidence validation reported unsupported references."
            )

        if total_count == 0:
            score = 30.0
            findings.append(
                "Answer contains no verifiable source-file or entity references."
            )
        else:
            reference_score = (
                supported_count / total_count
            ) * 100.0

            score = reference_score

            if supported_count:
                findings.append(
                    f"{supported_count} answer reference(s) are supported "
                    "by the retrieved context."
                )

        if (
            not response.evidence_sufficient
            or not evidence_result.evidence_sufficient
        ):
            score = min(score, 40.0)

        if not evidence_result.is_valid:
            score = min(score, 50.0)

        if not context.context_text.strip():
            score = min(score, 30.0)

        score = max(0.0, min(100.0, score))

        return AnswerQualityDimension(
            name="evidence_grounding",
            score=round(score, 2),
            weight=cls.DIMENSION_WEIGHTS["evidence_grounding"],
            findings=tuple(findings),
        )

    @staticmethod
    def _split_sentences(text: str) -> tuple[str, ...]:
        """Split text into simple sentence units."""

        return tuple(
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
            if sentence.strip()
        )

    @classmethod
    def _find_repeated_words(
        cls,
        words: list[str],
    ) -> tuple[str, ...]:
        """Find unusually repeated meaningful words."""

        normalized = [
            re.sub(r"[^a-zA-Z0-9_]", "", word).casefold()
            for word in words
        ]

        counts = {}

        for word in normalized:
            if (
                len(word) > 3
                and word not in cls.STOP_WORDS
            ):
                counts[word] = counts.get(word, 0) + 1

        return tuple(
            sorted(
                word
                for word, count in counts.items()
                if count >= 4
            )
        )

    @classmethod
    def _determine_quality_level(
        cls,
        score: float,
    ) -> str:
        """Map an overall score to a quality level."""

        if score >= cls.EXCELLENT_THRESHOLD:
            return AnswerQualityLevel.EXCELLENT

        if score >= cls.GOOD_THRESHOLD:
            return AnswerQualityLevel.GOOD

        if score >= cls.FAIR_THRESHOLD:
            return AnswerQualityLevel.FAIR

        return AnswerQualityLevel.POOR
