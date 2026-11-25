
"""Validate user questions before codebase intelligence processing."""

from dataclasses import dataclass


class QuestionValidationError(ValueError):
    """Raised when a user question is invalid."""


@dataclass(frozen=True)
class ValidatedQuestion:
    """A validated and normalized user question."""

    question: str
    character_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question:
            raise QuestionValidationError(
                "Validated question must be a non-empty string."
            )

        if self.question != self.question.strip():
            raise QuestionValidationError(
                "Validated question must not contain surrounding whitespace."
            )

        if self.character_count != len(self.question):
            raise QuestionValidationError(
                "Character count does not match the question length."
            )


class QuestionValidationService:
    """Validate and normalize questions submitted by users."""

    DEFAULT_MAX_LENGTH = 2000

    def __init__(self, max_length: int = DEFAULT_MAX_LENGTH) -> None:
        if (
            isinstance(max_length, bool)
            or not isinstance(max_length, int)
            or max_length <= 0
        ):
            raise QuestionValidationError(
                "Maximum question length must be a positive integer."
            )

        self.max_length = max_length

    def validate(self, question: str) -> ValidatedQuestion:
        """
        Validate a question and return its normalized representation.

        Args:
            question: The question submitted by the user.

        Returns:
            A ValidatedQuestion containing the trimmed question.

        Raises:
            QuestionValidationError: If the question is invalid.
        """
        if not isinstance(question, str):
            raise QuestionValidationError(
                "Question must be a string."
            )

        normalized_question = question.strip()

        if not normalized_question:
            raise QuestionValidationError(
                "Question cannot be empty."
            )

        if len(normalized_question) > self.max_length:
            raise QuestionValidationError(
                f"Question exceeds the maximum length of "
                f"{self.max_length} characters."
            )

        if "\x00" in normalized_question:
            raise QuestionValidationError(
                "Question cannot contain null characters."
            )

        return ValidatedQuestion(
            question=normalized_question,
            character_count=len(normalized_question),
        )
