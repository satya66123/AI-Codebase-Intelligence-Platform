
"""Main Streamlit application navigation and page rendering."""

import streamlit as st

from appy.application import ApplicationContainer
from appy.presentation.code_quality_view import render_code_quality_view
from appy.presentation.repository_discovery_view import (
    SESSION_SOURCE_RESULT_KEY,
    render_repository_discovery_view,
)


def render_home(container: ApplicationContainer) -> None:
    """Render the application home page."""

    st.title("🤖 AI Codebase Intelligence Platform")

    st.markdown(
        """
        Welcome to the AI Codebase Intelligence Agent Platform.

        The platform is built with a multi-provider,
        multi-model architecture.
        """
    )

    service = container.create_provider_model_service()
    providers = service.get_providers()

    st.subheader("AI Providers")

    provider = st.selectbox(
        "Select Provider",
        providers,
    )

    models = service.get_models(provider)
    model_names = [model.name for model in models]

    st.selectbox(
        "Select Model",
        model_names,
    )


def render_repository_discovery(container: ApplicationContainer) -> None:
    """Render repository discovery and source parsing."""

    discovery_service = (
        container.create_repository_discovery_integration_service()
    )

    source_loading_service = (
        container.create_repository_source_loading_service()
    )

    render_repository_discovery_view(
        discovery_service,
        source_loading_service,
    )


def render_code_quality(container: ApplicationContainer) -> None:
    """Render code quality analysis for the loaded repository."""

    loading_result = st.session_state.get(SESSION_SOURCE_RESULT_KEY)

    if loading_result is None:
        st.header("Code Quality Analysis")
        st.info(
            "Please discover a repository and load its source files "
            "from the Repository Discovery page first."
        )
        return

    source_files = loading_result.source_files

    quality_service = container.create_code_quality_analysis_service()

    render_code_quality_view(
        source_files=source_files,
        service=quality_service,
    )


def render(container: ApplicationContainer) -> None:
    """Render the application navigation and selected page."""

    st.sidebar.title("Navigation")

    selected_page = st.sidebar.radio(
        "Select Page",
        [
            "Home",
            "Repository Discovery",
            "Code Quality Analysis",
        ],
    )

    if selected_page == "Home":
        render_home(container)

    elif selected_page == "Repository Discovery":
        render_repository_discovery(container)

    elif selected_page == "Code Quality Analysis":
        render_code_quality(container)
