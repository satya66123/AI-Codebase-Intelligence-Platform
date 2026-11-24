
from app.application.container import ApplicationContainer
from app.application.repository_discovery_integration_service import (
    RepositoryDiscoveryIntegrationService,
)


def test_container_creates_repository_discovery_service():
    container = ApplicationContainer()

    service = (
        container.create_repository_discovery_integration_service()
    )

    assert isinstance(
        service,
        RepositoryDiscoveryIntegrationService,
    )


def test_container_reuses_repository_discovery_service():
    container = ApplicationContainer()

    first_service = (
        container.create_repository_discovery_integration_service()
    )

    second_service = (
        container.create_repository_discovery_integration_service()
    )

    assert first_service is second_service


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
