
from dataclasses import dataclass

from app.application.context_builder import ContextBuildResult
from app.application.reasoning_response_model import ReasoningResponse


class EvidenceValidationError(ValueError):
    """Raised when evidence validation receives invalid input."""


@dataclass(frozen=True)
class EvidenceValidationResult:
    """Contains the outcome of repository evidence-reference validation."""

    is_valid: bool
    evidence_sufficient: bool
    supported_source_files: tuple[str, ...]
    unsupported_source_files: tuple[str, ...]
    supported_entity_ids: tuple[str, ...]
    unsupported_entity_ids: tuple[str, ...]
    issues: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.is_valid, bool):
            raise EvidenceValidationError(
                "is_valid must be a boolean."
            )

        if not isinstance(self.evidence_sufficient, bool):
            raise EvidenceValidationError(
                "evidence_sufficient must be a boolean."
            )

        tuple_fields = (
            "supported_source_files",
            "unsupported_source_files",
            "supported_entity_ids",
            "unsupported_entity_ids",
            "issues",
        )

        for field_name in tuple_fields:
            value = getattr(self, field_name)

            if not isinstance(value, tuple):
                raise EvidenceValidationError(
                    f"{field_name} must be a tuple."
                )

            if any(
                not isinstance(item, str) or not item.strip()
                for item in value
            ):
                raise EvidenceValidationError(
                    f"{field_name} must contain non-empty strings."
                )


class EvidenceValidationAgent:
    """
    Validates answer references against the retrieved repository context.

    This agent checks reference integrity. It does not claim to prove
    the semantic correctness of every statement in an AI-generated answer.
    """

    def validate(
        self,
        response: ReasoningResponse,
        context: ContextBuildResult,
    ) -> EvidenceValidationResult:
        """
        Validate source-file and entity references in a reasoning response.
        """

        self._validate_inputs(response, context)

        context_source_files = set(context.source_files)
        context_entity_ids = set(context.entity_ids)

        response_source_files = tuple(response.source_files)
        response_entity_ids = tuple(response.entity_ids)

        supported_source_files = tuple(
            source_file
            for source_file in response_source_files
            if source_file in context_source_files
        )

        unsupported_source_files = tuple(
            source_file
            for source_file in response_source_files
            if source_file not in context_source_files
        )

        supported_entity_ids = tuple(
            entity_id
            for entity_id in response_entity_ids
            if entity_id in context_entity_ids
        )

        unsupported_entity_ids = tuple(
            entity_id
            for entity_id in response_entity_ids
            if entity_id not in context_entity_ids
        )

        issues = []

        if unsupported_source_files:
            issues.append(
                "Response contains source files not present in "
                "the retrieved context."
            )

        if unsupported_entity_ids:
            issues.append(
                "Response contains entity IDs not present in "
                "the retrieved context."
            )

        is_valid = not issues

        return EvidenceValidationResult(
            is_valid=is_valid,
            evidence_sufficient=response.evidence_sufficient,
            supported_source_files=supported_source_files,
            unsupported_source_files=unsupported_source_files,
            supported_entity_ids=supported_entity_ids,
            unsupported_entity_ids=unsupported_entity_ids,
            issues=tuple(issues),
        )

    @staticmethod
    def _validate_inputs(
        response: ReasoningResponse,
        context: ContextBuildResult,
    ) -> None:
        """Validate the input model types and reference collections."""

        if not isinstance(response, ReasoningResponse):
            raise EvidenceValidationError(
                "response must be a ReasoningResponse instance."
            )

        if not isinstance(context, ContextBuildResult):
            raise EvidenceValidationError(
                "context must be a ContextBuildResult instance."
            )

        if not isinstance(response.source_files, tuple):
            raise EvidenceValidationError(
                "Response source_files must be a tuple."
            )

        if not isinstance(response.entity_ids, tuple):
            raise EvidenceValidationError(
                "Response entity_ids must be a tuple."
            )

        if not isinstance(context.source_files, tuple):
            raise EvidenceValidationError(
                "Context source_files must be a tuple."
            )

        if not isinstance(context.entity_ids, tuple):
            raise EvidenceValidationError(
                "Context entity_ids must be a tuple."
            )

        for source_file in (
            response.source_files + context.source_files
        ):
            if not isinstance(source_file, str) or not source_file.strip():
                raise EvidenceValidationError(
                    "Source file references must be non-empty strings."
                )

        for entity_id in (
            response.entity_ids + context.entity_ids
        ):
            if not isinstance(entity_id, str) or not entity_id.strip():
                raise EvidenceValidationError(
                    "Entity references must be non-empty strings."
                )
