
"""Integrates advanced repository investigation, reporting, and evaluation."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from appy.application.advanced_code_investigation_agent import (
    AdvancedCodeInvestigationAgent,
    AdvancedCodeInvestigationError,
)
from appy.application.architecture_intelligence_report_service import (
    ArchitectureIntelligenceReportService,
    ArchitectureIntelligenceReportError,
)
from appy.application.advanced_analysis_evaluation_service import (
    AdvancedAnalysisEvaluationService,
    AdvancedAnalysisEvaluationError,
)


class AdvancedIntelligenceIntegrationError(ValueError):
    """Raised when advanced intelligence integration fails."""

    def __init__(self, message: str, stage: str | None = None) -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class AdvancedIntelligenceIntegrationResult:
    """Unified result from advanced investigation, reporting, and evaluation."""

    investigation_result: Any
    report: Any
    evaluation: Any
    completed_stages: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "investigation_result",
            "report",
            "evaluation",
        ):
            if getattr(self, field_name) is None:
                raise AdvancedIntelligenceIntegrationError(
                    f"{field_name} cannot be None."
                )

        if not isinstance(self.completed_stages, tuple):
            raise AdvancedIntelligenceIntegrationError(
                "completed_stages must be a tuple."
            )

        if any(
            not isinstance(stage, str) or not stage.strip()
            for stage in self.completed_stages
        ):
            raise AdvancedIntelligenceIntegrationError(
                "completed_stages must contain non-empty strings."
            )

        expected = (
            "investigation",
            "report",
            "evaluation",
        )
        if self.completed_stages != expected:
            raise AdvancedIntelligenceIntegrationError(
                "completed_stages must contain all stages in execution order."
            )

    @property
    def is_complete(self) -> bool:
        return len(self.completed_stages) == 3

    @property
    def overall_score(self) -> float:
        return self.evaluation.overall_score

    @property
    def overall_level(self) -> Any:
        return self.evaluation.overall_level

    @property
    def recommendations(self) -> tuple[str, ...]:
        return self.evaluation.recommendations

    @property
    def report_text(self) -> str:
        return self.report.report_text


class AdvancedIntelligenceIntegrationService:
    """Coordinates advanced investigation, report generation, and evaluation."""

    def __init__(
        self,
        investigation_agent: AdvancedCodeInvestigationAgent | None = None,
        report_service: ArchitectureIntelligenceReportService | None = None,
        evaluation_service: AdvancedAnalysisEvaluationService | None = None,
    ) -> None:
        self.investigation_agent = (
            investigation_agent
            if investigation_agent is not None
            else AdvancedCodeInvestigationAgent()
        )
        self.report_service = (
            report_service
            if report_service is not None
            else ArchitectureIntelligenceReportService()
        )
        self.evaluation_service = (
            evaluation_service
            if evaluation_service is not None
            else AdvancedAnalysisEvaluationService()
        )

    def integrate(
        self,
        parsed_sources: Mapping[str, Any],
        source_files: Any = None,
        code_entities: Any = (),
        dependencies: Any = (),
        call_graphs: Any = (),
        entry_points: Any = None,
        max_depth: int = 10,
        change_impact_result: Any = None,
        direct_indirect_impact_result: Any = None,
    ) -> AdvancedIntelligenceIntegrationResult:
        """Run the complete advanced intelligence integration workflow."""

        self._validate_parsed_sources(parsed_sources)

        try:
            investigation_result = self.investigation_agent.investigate(
                parsed_sources=parsed_sources,
                source_files=source_files,
                code_entities=code_entities,
                dependencies=dependencies,
                call_graphs=call_graphs,
                entry_points=entry_points,
                max_depth=max_depth,
            )
        except Exception as exc:
            raise AdvancedIntelligenceIntegrationError(
                f"Advanced investigation failed: {exc}",
                stage="investigation",
            ) from exc

        try:
            report = self.report_service.generate(
                investigation_result
            )
        except Exception as exc:
            raise AdvancedIntelligenceIntegrationError(
                f"Architecture report generation failed: {exc}",
                stage="report",
            ) from exc

        try:
            evaluation = self.evaluation_service.evaluate(
                investigation_result=investigation_result,
                report=report,
                change_impact_result=change_impact_result,
                direct_indirect_impact_result=direct_indirect_impact_result,
            )
        except Exception as exc:
            raise AdvancedIntelligenceIntegrationError(
                f"Advanced analysis evaluation failed: {exc}",
                stage="evaluation",
            ) from exc

        return AdvancedIntelligenceIntegrationResult(
            investigation_result=investigation_result,
            report=report,
            evaluation=evaluation,
            completed_stages=(
                "investigation",
                "report",
                "evaluation",
            ),
        )

    @staticmethod
    def _validate_parsed_sources(
        parsed_sources: Mapping[str, Any],
    ) -> None:
        if not isinstance(parsed_sources, Mapping):
            raise AdvancedIntelligenceIntegrationError(
                "parsed_sources must be a mapping of filenames to ParsedSource objects.",
                stage="validation",
            )

        if not parsed_sources:
            raise AdvancedIntelligenceIntegrationError(
                "parsed_sources must not be empty.",
                stage="validation",
            )
