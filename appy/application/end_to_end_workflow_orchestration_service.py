
"""Orchestrate the end-to-end advanced codebase intelligence workflow."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from appy.application.advanced_intelligence_integration_service import (
    AdvancedIntelligenceIntegrationService,
)


class EndToEndWorkflowOrchestrationError(ValueError):
    """Raised when the end-to-end workflow cannot be completed."""

    def __init__(self, message: str, stage: str = "workflow") -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class EndToEndWorkflowResult:
    """Immutable result produced by the end-to-end workflow."""

    repository_file_count: int
    integration_result: Any
    completed_stages: tuple[str, ...]
    workflow_summary: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.repository_file_count, bool)
            or not isinstance(self.repository_file_count, int)
            or self.repository_file_count <= 0
        ):
            raise ValueError("repository_file_count must be a positive integer")

        if self.integration_result is None:
            raise ValueError("integration_result cannot be None")

        if not isinstance(self.completed_stages, tuple):
            raise ValueError("completed_stages must be a tuple")

        if any(
            not isinstance(stage, str) or not stage.strip()
            for stage in self.completed_stages
        ):
            raise ValueError("completed_stages must contain non-empty strings")

        expected_stages = (
            "input_validation",
            "advanced_intelligence_integration",
            "workflow_completed",
        )

        if self.completed_stages != expected_stages:
            raise ValueError("completed_stages does not match the workflow sequence")

        if not isinstance(self.workflow_summary, str) or not self.workflow_summary.strip():
            raise ValueError("workflow_summary must be a non-empty string")

    @property
    def is_complete(self) -> bool:
        """Return whether every workflow stage completed."""

        return self.completed_stages[-1] == "workflow_completed"

    @property
    def report(self) -> Any:
        """Return the architecture intelligence report."""

        return getattr(self.integration_result, "report", None)

    @property
    def evaluation(self) -> Any:
        """Return the advanced analysis evaluation."""

        return getattr(self.integration_result, "evaluation", None)

    @property
    def investigation_result(self) -> Any:
        """Return the advanced code investigation result."""

        return getattr(self.integration_result, "investigation_result", None)


class EndToEndWorkflowOrchestrationService:
    """Coordinate validation and advanced intelligence integration."""

    def __init__(
        self,
        integration_service: AdvancedIntelligenceIntegrationService | None = None,
    ) -> None:
        self.integration_service = (
            integration_service
            if integration_service is not None
            else AdvancedIntelligenceIntegrationService()
        )

    def execute(
        self,
        parsed_sources: Mapping[str, Any],
        source_files: Mapping[str, str] | None = None,
        code_entities: tuple[Any, ...] = (),
        dependencies: tuple[Any, ...] = (),
        call_graphs: tuple[Any, ...] = (),
        entry_points: Any = None,
        max_depth: int = 10,
        change_impact_result: Any = None,
        direct_indirect_impact_result: Any = None,
    ) -> EndToEndWorkflowResult:
        """Execute the complete advanced-intelligence workflow."""

        self._validate_parsed_sources(parsed_sources)

        repository_file_count = len(parsed_sources)

        try:
            integration_result = self.integration_service.integrate(
                parsed_sources=parsed_sources,
                source_files=source_files,
                code_entities=code_entities,
                dependencies=dependencies,
                call_graphs=call_graphs,
                entry_points=entry_points,
                max_depth=max_depth,
                change_impact_result=change_impact_result,
                direct_indirect_impact_result=direct_indirect_impact_result,
            )
        except Exception as exc:
            raise EndToEndWorkflowOrchestrationError(
                f"End-to-end workflow integration failed: {exc}",
                stage="advanced_intelligence_integration",
            ) from exc

        if integration_result is None:
            raise EndToEndWorkflowOrchestrationError(
                "Advanced intelligence integration returned no result.",
                stage="advanced_intelligence_integration",
            )

        return EndToEndWorkflowResult(
            repository_file_count=repository_file_count,
            integration_result=integration_result,
            completed_stages=(
                "input_validation",
                "advanced_intelligence_integration",
                "workflow_completed",
            ),
            workflow_summary=(
                "End-to-end advanced codebase intelligence workflow "
                f"completed successfully for {repository_file_count} files."
            ),
        )

    @staticmethod
    def _validate_parsed_sources(parsed_sources: Mapping[str, Any]) -> None:
        """Validate the parsed repository source collection."""

        if not isinstance(parsed_sources, Mapping):
            raise EndToEndWorkflowOrchestrationError(
                "parsed_sources must be a mapping.",
                stage="input_validation",
            )

        if not parsed_sources:
            raise EndToEndWorkflowOrchestrationError(
                "parsed_sources cannot be empty.",
                stage="input_validation",
            )

        for filename, parsed_source in parsed_sources.items():
            if not isinstance(filename, str) or not filename.strip():
                raise EndToEndWorkflowOrchestrationError(
                    "Every parsed source must have a non-empty filename.",
                    stage="input_validation",
                )

            if parsed_source is None:
                raise EndToEndWorkflowOrchestrationError(
                    f"Parsed source for '{filename}' cannot be None.",
                    stage="input_validation",
                )
