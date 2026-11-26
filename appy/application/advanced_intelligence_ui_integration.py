
"""Streamlit presentation integration for advanced codebase intelligence."""

from collections.abc import Mapping
from contextlib import nullcontext
from typing import Any

from appy.application.final_application_integration_service import (
    FinalApplicationIntegrationService,
)


class AdvancedIntelligenceUIIntegrationError(ValueError):
    """Raised when advanced intelligence UI integration fails."""


class AdvancedIntelligenceUIIntegration:
    """Render and execute advanced codebase intelligence in Streamlit."""

    def __init__(
        self,
        application_service: FinalApplicationIntegrationService | None = None,
        ui: Any = None,
    ) -> None:
        self.application_service = (
            application_service
            if application_service is not None
            else FinalApplicationIntegrationService()
        )
        self.ui = ui

    def render(
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
        button_label: str = "Run Advanced Intelligence Analysis",
        button_key: str = "advanced_intelligence_analysis",
        existing_result: Any = None,
    ) -> Any:
        """Render the analysis interface and preserve previous results."""

        ui = self._get_ui()

        ui.subheader("Advanced Codebase Intelligence")
        ui.caption(
            "Run the complete advanced analysis workflow and review its "
            "investigation, architecture report, and evaluation results."
        )

        if not isinstance(parsed_sources, Mapping):
            ui.error("Parsed repository sources must be provided as a mapping.")
            return None

        if not parsed_sources:
            ui.info("Load and parse repository files before running the analysis.")
            return None

        should_run = ui.button(button_label, key=button_key)

        if not should_run:
            if self._is_successful(existing_result):
                self._render_result(ui, existing_result)
                return existing_result

            return None

        try:
            with self._spinner(ui, "Running advanced intelligence analysis..."):
                result = self.application_service.execute(
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
            ui.error(f"Advanced intelligence analysis failed: {exc}")
            return None

        if not self._is_successful(result):
            ui.error(
                "Advanced intelligence analysis did not complete successfully."
            )
            return None

        self._render_result(ui, result)
        return result

    @staticmethod
    def _is_successful(result: Any) -> bool:
        """Check whether a result represents successful analysis."""

        return (
            result is not None
            and getattr(result, "is_successful", False) is True
        )

    def _get_ui(self) -> Any:
        """Return the injected UI module or import Streamlit lazily."""

        if self.ui is not None:
            return self.ui

        try:
            import streamlit as st
        except ImportError as exc:
            raise AdvancedIntelligenceUIIntegrationError(
                "Streamlit is required to render the advanced intelligence UI."
            ) from exc

        return st

    @staticmethod
    def _spinner(ui: Any, message: str) -> Any:
        """Return a spinner context when supported by the UI."""

        spinner = getattr(ui, "spinner", None)

        if callable(spinner):
            return spinner(message)

        return nullcontext()

    def render_result(self, result: Any) -> bool:
        """Render an existing successful result without executing analysis."""

        if not self._is_successful(result):
            return False

        self._render_result(self._get_ui(), result)
        return True

    def _render_result(self, ui: Any, result: Any) -> None:
        """Render the successful application result."""

        ui.success(
            getattr(result, "message", "Analysis completed successfully.")
        )

        file_count = getattr(result, "repository_file_count", 0)
        ui.metric("Repository files analyzed", file_count)

        evaluation = getattr(result, "evaluation", None)

        if evaluation is not None:
            score = getattr(evaluation, "overall_score", None)
            level = getattr(evaluation, "overall_level", None)

            if score is not None:
                ui.metric("Advanced analysis score", score)

            if level is not None:
                ui.write(f"Evaluation level: {level}")

        report = getattr(result, "report", None)
        report_text = getattr(report, "report_text", None) if report else None

        if report_text:
            with ui.expander(
                "Architecture Intelligence Report",
                expanded=True,
            ):
                ui.markdown(report_text)

        investigation = getattr(result, "investigation_result", None)

        if investigation is not None:
            with ui.expander(
                "Investigation Summary",
                expanded=False,
            ):
                summary = getattr(
                    investigation,
                    "investigation_summary",
                    None,
                )

                ui.write(summary or "Investigation completed.")

        recommendations = (
            getattr(evaluation, "recommendations", ())
            if evaluation
            else ()
        )

        if recommendations:
            with ui.expander(
                "Recommendations",
                expanded=False,
            ):
                for recommendation in recommendations:
                    ui.write(f"- {recommendation}")

        completed_stages = getattr(result, "completed_stages", ())

        if completed_stages:
            with ui.expander(
                "Completed Workflow Stages",
                expanded=False,
            ):
                for stage in completed_stages:
                    ui.write(f"- {stage}")
