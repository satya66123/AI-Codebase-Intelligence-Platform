
from appy.application.container import ApplicationContainer
from appy.application.repository_source_loading_service import (
    RepositorySourceLoadingService,
)


def test_container_creates_repository_source_loading_service():
    container = ApplicationContainer()

    service = container.create_repository_source_loading_service()

    assert isinstance(service, RepositorySourceLoadingService)


def test_container_reuses_repository_source_loading_service():
    container = ApplicationContainer()

    first = container.create_repository_source_loading_service()
    second = container.create_repository_source_loading_service()

    assert first is second


def test_container_creates_source_loading_service_independently():
    container = ApplicationContainer()

    discovery_service = (
        container.create_repository_discovery_integration_service()
    )
    loading_service = (
        container.create_repository_source_loading_service()
    )

    assert discovery_service is not loading_service


def test_container_preserves_repository_discovery_service():
    container = ApplicationContainer()

    first = container.create_repository_discovery_integration_service()
    second = container.create_repository_discovery_integration_service()

    assert first is second


def test_container_preserves_provider_factory():
    container = ApplicationContainer()

    assert container.provider_factory is not None


def test_container_preserves_provider_registry():
    container = ApplicationContainer()

    assert container.provider_registry is not None


def test_container_preserves_provider_model_service():
    container = ApplicationContainer()

    service = container.create_provider_model_service()

    assert service is not None


def test_container_registers_eight_ai_providers():
    container = ApplicationContainer()

    expected_providers = {
        "ollama",
        "openai",
        "anthropic",
        "gemini",
        "mistral",
        "groq",
        "cohere",
        "deepseek",
    }

    assert set(container.provider_factory.supported_providers()) == (
        expected_providers
    )
