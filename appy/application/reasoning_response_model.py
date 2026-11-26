
from dataclasses import dataclass
from typing import Any

from appy.application.intent_detection_service import QueryIntent


class ReasoningResponseError(ValueError):
    """Raised when reasoning response data is invalid."""


@dataclass(frozen=True)
class ReasoningResponse:
    """Immutable structured result of codebase reasoning."""

    question: str
    answer: str
    intent: QueryIntent
    source_files: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    provider_name: str = ""
    model_name: str = ""
    evidence_sufficient: bool = True

    def __post_init__(self) -> None:
        self._validate_text(self.question, "question")
        self._validate_text(self.answer, "answer")

        if not isinstance(self.intent, QueryIntent):
            raise ReasoningResponseError(
                "intent must be a valid QueryIntent."
            )

        self._validate_references(self.source_files, "source_files")
        self._validate_references(self.entity_ids, "entity_ids")

        self._validate_optional_text(
            self.provider_name,
            "provider_name",
        )
        self._validate_optional_text(
            self.model_name,
            "model_name",
        )

        if not isinstance(self.evidence_sufficient, bool):
            raise ReasoningResponseError(
                "evidence_sufficient must be a boolean."
            )

        object.__setattr__(self, "question", self.question.strip())
        object.__setattr__(self, "answer", self.answer.strip())
        object.__setattr__(
            self,
            "provider_name",
            self.provider_name.strip().lower(),
        )
        object.__setattr__(
            self,
            "model_name",
            self.model_name.strip(),
        )

        object.__setattr__(
            self,
            "source_files",
            self._normalize_references(self.source_files),
        )
        object.__setattr__(
            self,
            "entity_ids",
            self._normalize_references(self.entity_ids),
        )

    @staticmethod
    def _validate_text(value: Any, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ReasoningResponseError(
                f"{field_name} must be a non-empty string."
            )

    @staticmethod
    def _validate_optional_text(value: Any, field_name: str) -> None:
        if not isinstance(value, str):
            raise ReasoningResponseError(
                f"{field_name} must be a string."
            )

    @classmethod
    def _validate_references(
        cls,
        references: Any,
        field_name: str,
    ) -> None:
        if not isinstance(references, (tuple, list)):
            raise ReasoningResponseError(
                f"{field_name} must be a tuple or list."
            )

        for reference in references:
            cls._validate_text(reference, field_name)

    @staticmethod
    def _normalize_references(
        references: tuple[str, ...] | list[str],
    ) -> tuple[str, ...]:
        normalized = []
        seen = set()

        for reference in references:
            value = reference.strip()
            if value not in seen:
                normalized.append(value)
                seen.add(value)

        return tuple(normalized)

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-friendly representation."""

        return {
            "question": self.question,
            "answer": self.answer,
            "intent": self.intent.name,
            "source_files": list(self.source_files),
            "entity_ids": list(self.entity_ids),
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "evidence_sufficient": self.evidence_sufficient,
        }
