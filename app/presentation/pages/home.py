import streamlit as st

from app.application import ApplicationContainer


def render(container: ApplicationContainer) -> None:
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