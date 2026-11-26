
"""Streamlit view for repository code quality analysis."""

from typing import Any, Mapping

import streamlit as st


SESSION_QUALITY_RESULT_KEY = "repository_code_quality_result"


def render_code_quality_view(
    source_files: Mapping[str, str],
    service: Any,
    ui: Any = None,
    session_state: Any = None,
) -> None:
    """Render code quality analysis and its repository findings."""

    interface = ui if ui is not None else st
    state = (
        session_state
        if session_state is not None
        else interface.session_state
    )

    interface.header("Code Quality Analysis")
    interface.caption(
        "Evaluate repository source files for quality, maintainability, "
        "complexity and Python syntax issues."
    )

    if not isinstance(source_files, Mapping):
        interface.error("Source files must be provided as a mapping.")
        return

    if not source_files:
        interface.info(
            "Discover a repository and load source files before "
            "running code quality analysis."
        )
        return

    interface.metric("Loaded Source Files", len(source_files))

    if interface.button(
        "Run Code Quality Analysis",
        key="run_code_quality_analysis",
    ):
        try:
            result = service.analyze(source_files=source_files)
            state[SESSION_QUALITY_RESULT_KEY] = result
            interface.success("Code quality analysis completed.")
        except Exception as exc:
            interface.error(f"Code quality analysis failed: {exc}")
            return

    result = state.get(SESSION_QUALITY_RESULT_KEY)

    if result is None:
        interface.info("Run the analysis to view quality results.")
        return

    _render_quality_summary(interface, result)
    _render_file_results(interface, result)
    _render_findings(interface, result)


def _render_quality_summary(ui: Any, result: Any) -> None:
    """Display repository-level quality metrics."""

    ui.subheader("Repository Quality Summary")

    ui.metric("Quality Score", f"{result.score:.1f}/100")
    ui.metric("Total Files", result.total_files)
    ui.metric("Analyzed Files", result.analyzed_files)
    ui.metric("Skipped Files", result.skipped_files)
    ui.metric("Lines of Code", result.total_lines_of_code)

    ui.metric("Errors", result.error_count)
    ui.metric("Warnings", result.warning_count)
    ui.metric("Information", result.info_count)

    if result.healthy:
        ui.success("No quality errors detected.")
    else:
        ui.warning("Quality errors were detected. Review the findings.")


def _render_file_results(ui: Any, result: Any) -> None:
    """Display per-file quality scores."""

    ui.subheader("File Quality Results")

    rows = [
        {
            "File": item.file_path,
            "Score": item.score,
            "Lines of Code": item.lines_of_code,
            "Findings": len(item.findings),
        }
        for item in result.file_results
    ]

    if rows:
        ui.dataframe(rows, use_container_width=True)
    else:
        ui.info("No files were analyzed by the quality service.")


def _render_findings(ui: Any, result: Any) -> None:
    """Display quality findings and their severity/category summaries."""

    ui.subheader("Findings by Severity")
    ui.json(result.findings_by_severity)

    ui.subheader("Findings by Category")
    ui.json(result.findings_by_category)

    ui.subheader("Detailed Findings")

    if not result.findings:
        ui.success("No quality findings were reported.")
        return

    rows = [
        {
            "Code": finding.code,
            "Severity": finding.severity.value,
            "Category": finding.category.value,
            "File": finding.file_path,
            "Line": finding.line,
            "Symbol": finding.symbol,
            "Message": finding.message,
        }
        for finding in result.findings
    ]

    ui.dataframe(rows, use_container_width=True)
