
"""Provide the final application-facing integration for codebase intelligence."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.application.end_to_end_workflow_orchestration_service import (
    EndToEndWorkflowOrchestrationService,
)


class FinalApplicationIntegrationError(ValueError):
    """Raised when final application integration fails."""

    def __init__(self, message: str, stage: str = "application_integration") -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class FinalApplicationIntegrationResult:
    """Immutable application-level result."""

    workflow_result: Any
    status: str
    message: str

    def __post_init__(self) -> None:
        if self.workflow_result is None:
            raise ValueError("workflow_result cannot be None")

        if self.status != "completed":
            raise ValueError("status must be 'completed'")

        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string")

        if not getattr(self.workflow_result, "is_complete", False):
            raise ValueError("workflow_result must be complete")

    @property
    def is_successful(self) -> bool:
        """Return whether application integration completed successfully."""

        return self.status == "completed"

    @property
    def report(self) -> Any:
        """Expose the generated architecture intelligence report."""

        return getattr(self.workflow_result, "report", None)

    @property
    def evaluation(self) -> Any:
        """Expose the advanced analysis evaluation."""

        return getattr(self.workflow_result, "evaluation", None)

    @property
    def investigation_result(self) -> Any:
        """Expose the advanced investigation result."""

        return getattr(self.workflow_result, "investigation_result", None)

    @property
    def repository_file_count(self) -> int:
        """Expose the number of repository files processed."""

        return self.workflow_result.repository_file_count

    @property
    def completed_stages(self) -> tuple[str, ...]:
        """Expose the workflow's completed stages."""

        return self.workflow_result.completed_stages


class FinalApplicationIntegrationService:
    """Expose one application-facing entry point for advanced analysis."""

    def __init__(
        self,
        workflow_service: EndToEndWorkflowOrchestrationService | None = None,
    ) -> None:
        self.workflow_service = (
            workflow_service
            if workflow_service is not None
            else EndToEndWorkflowOrchestrationService()
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
    ) -> FinalApplicationIntegrationResult:
        """Execute the complete workflow and return an application result."""

        if not isinstance(parsed_sources, Mapping):
            raise FinalApplicationIntegrationError(
                "parsed_sources must be a mapping.",
                stage="input_validation",
            )

        if not parsed_sources:
            raise FinalApplicationIntegrationError(
                "parsed_sources cannot be empty.",
                stage="input_validation",
            )

        try:
            workflow_result = self.workflow_service.execute(
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
            stage = getattr(exc, "stage", "workflow_execution")
            raise FinalApplicationIntegrationError(
                f"Final application integration failed: {exc}",
                stage=stage,
            ) from exc

        if workflow_result is None:
            raise FinalApplicationIntegrationError(
                "Workflow orchestration returned no result.",
                stage="workflow_execution",
            )

        if not getattr(workflow_result, "is_complete", False):
            raise FinalApplicationIntegrationError(
                "Workflow orchestration returned an incomplete result.",
                stage="workflow_validation",
            )

        return FinalApplicationIntegrationResult(
            workflow_result=workflow_result,
            status="completed",
            message=(
                "Final application integration completed successfully for "
                f"{workflow_result.repository_file_count} repository files."
            ),
        )
