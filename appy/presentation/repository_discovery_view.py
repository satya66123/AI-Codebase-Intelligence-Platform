
"""Streamlit interface for repository discovery and code intelligence."""

from dataclasses import asdict, is_dataclass
from typing import Any

import streamlit as st

from appy.application.advanced_intelligence_ui_integration import (
    AdvancedIntelligenceUIIntegration,
)


SESSION_RESULT_KEY = "repository_discovery_result"
SESSION_SOURCE_RESULT_KEY = "repository_source_loading_result"
SESSION_ADVANCED_RESULT_KEY = "advanced_intelligence_result"


def render_repository_discovery_view(
    service: Any,
    source_loading_service: Any = None,
    advanced_intelligence_ui: Any = None,
) -> None:
    """Render repository discovery, parsing and advanced intelligence."""

    st.header("Repository Discovery")
    st.caption(
        "Explore repository structure, files, languages and metadata."
    )

    repository_path = st.text_input(
        "Local repository path",
        placeholder="C:/Users/user/PycharmProjects/my-project",
        key="repository_discovery_path",
    )

    if st.button(
        "Discover Repository",
        key="discover_repository_button",
    ):
        if not repository_path.strip():
            st.error("Please enter a repository path.")
        else:
            try:
                result = service.discover(repository_path)

                st.session_state[SESSION_RESULT_KEY] = result
                st.session_state.pop(SESSION_SOURCE_RESULT_KEY, None)
                st.session_state.pop(SESSION_ADVANCED_RESULT_KEY, None)

                st.success("Repository discovery completed.")
            except Exception as exc:
                st.error(f"Repository discovery failed: {exc}")

    result = st.session_state.get(SESSION_RESULT_KEY)

    if result is None:
        st.info("Enter a repository path to begin discovery.")
        return

    service.restore_result(result)
    metadata = result.metadata

    st.subheader("Repository Overview")
    st.write("Repository:", result.repository.name)
    st.write("Location:", str(result.repository.root))

    st.metric("Total Files", metadata["total_files"])
    st.metric("Total Directories", metadata["total_directories"])
    st.metric("Total Size (Bytes)", metadata["total_size_bytes"])

    st.subheader("Programming Languages")
    st.json(metadata["languages"])

    st.subheader("Repository Structure")
    st.code(result.repository_map, language="text")

    st.subheader("File Metadata")

    file_rows = [
        asdict(item) if is_dataclass(item) else item
        for item in metadata["files"]
    ]

    if file_rows:
        st.dataframe(file_rows, use_container_width=True)
    else:
        st.info("No files were discovered.")

    _render_repository_search(service)

    if source_loading_service is None:
        return

    loading_result = _render_source_loading(
        result=result,
        metadata=metadata,
        source_loading_service=source_loading_service,
    )

    if loading_result is None:
        return

    _render_advanced_intelligence(
        loading_result=loading_result,
        advanced_intelligence_ui=advanced_intelligence_ui,
    )


def _render_repository_search(service: Any) -> None:
    """Render repository file search."""

    st.subheader("Search Repository Files")

    search_query = st.text_input(
        "Search by filename, path, extension or language",
        key="repository_discovery_search",
    )

    if not search_query.strip():
        return

    try:
        search_results = service.search_files(search_query)
        st.write(f"Matching files: {len(search_results)}")

        if search_results:
            st.dataframe(search_results, use_container_width=True)
        else:
            st.info("No matching files found.")
    except Exception as exc:
        st.error(f"Repository search failed: {exc}")


def _render_source_loading(
    result: Any,
    metadata: dict,
    source_loading_service: Any,
) -> Any:
    """Render source loading and parsing."""

    st.divider()
    st.subheader("Source Code Loading & Parsing")
    st.caption(
        "Load supported source files and parse them using registered "
        "language parsers."
    )

    if st.button(
        "Load and Parse Source Files",
        key="load_parse_source_files_button",
    ):
        try:
            loading_result = source_loading_service.load_and_parse(
                repository_path=result.repository.root,
                file_metadata=metadata["files"],
            )

            st.session_state[SESSION_SOURCE_RESULT_KEY] = loading_result
            st.session_state.pop(SESSION_ADVANCED_RESULT_KEY, None)

            st.success("Source loading and parsing completed.")
        except Exception as exc:
            st.error(f"Source loading failed: {exc}")

    loading_result = st.session_state.get(SESSION_SOURCE_RESULT_KEY)

    if loading_result is None:
        st.info("Select Load and Parse Source Files to begin code parsing.")
        return None

    st.subheader("Source Parsing Summary")

    st.metric("Selected Source Files", loading_result.selected_file_count)
    st.metric("Successfully Parsed", loading_result.parsed_file_count)
    st.metric("Skipped Files", loading_result.skipped_file_count)
    st.metric("Failed Files", loading_result.failed_file_count)

    st.write("Language distribution")
    st.json(dict(loading_result.language_counts))

    if loading_result.parsed_sources:
        st.subheader("Successfully Parsed Files")

        parsed_rows = [
            {
                "File": filename,
                "Language": parsed.language,
                "Lines": parsed.line_count,
            }
            for filename, parsed in loading_result.parsed_sources.items()
        ]

        st.dataframe(parsed_rows, use_container_width=True)

    if loading_result.failures:
        st.subheader("Skipped or Failed Files")

        failure_rows = [
            {
                "File": failure.filename,
                "Language": failure.language,
                "Stage": failure.stage,
                "Reason": failure.reason,
            }
            for failure in loading_result.failures
        ]

        st.dataframe(failure_rows, use_container_width=True)

    return loading_result


def _render_advanced_intelligence(
    loading_result: Any,
    advanced_intelligence_ui: Any = None,
) -> None:
    """Execute advanced intelligence and preserve its successful result."""

    st.divider()
    st.subheader("Advanced Codebase Intelligence")

    if not loading_result.parsed_sources:
        st.warning(
            "No source files were successfully parsed. "
            "Advanced intelligence analysis is unavailable."
        )
        return

    integration = advanced_intelligence_ui

    if integration is None:
        integration = AdvancedIntelligenceUIIntegration(ui=st)

    existing_result = st.session_state.get(SESSION_ADVANCED_RESULT_KEY)

    # Advanced investigation expects an ordered iterable of filenames,
    # not the mapping of filenames to source-code contents.
    source_filenames = tuple(loading_result.source_files.keys())

    result = integration.render(
        parsed_sources=loading_result.parsed_sources,
        source_files=source_filenames,
        existing_result=existing_result,
    )

    if result is not None and getattr(result, "is_successful", False):
        st.session_state[SESSION_ADVANCED_RESULT_KEY] = result
