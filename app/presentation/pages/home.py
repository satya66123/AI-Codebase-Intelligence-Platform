
import streamlit as st

from app.application import ApplicationContainer
from app.presentation.repository_discovery_view import (
    render_repository_discovery_view,
)


def render_home(container: ApplicationContainer) -> None:
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

    model_names = [
        model.name
        for model in models
    ]

    st.selectbox(
        "Select Model",
        model_names,
    )


def render(container: ApplicationContainer) -> None:
    st.sidebar.title("Navigation")

    selected_page = st.sidebar.radio(
        "Select Page",
        [
            "Home",
            "Repository Discovery",
        ],
    )

    if selected_page == "Home":
        render_home(container)

    elif selected_page == "Repository Discovery":
        service = (
            container
            .create_repository_discovery_integration_service()
        )

        render_repository_discovery_view(service)
