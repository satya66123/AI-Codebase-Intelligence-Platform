
from appy.application.container import ApplicationContainer
from appy.application.code_quality_analysis_service import (
    CodeQualityAnalysisService,
)


def test_container_creates_code_quality_service():
    container = ApplicationContainer()

    service = container.create_code_quality_analysis_service()

    assert isinstance(service, CodeQualityAnalysisService)


def test_container_reuses_code_quality_service():
    container = ApplicationContainer()

    first = container.create_code_quality_analysis_service()
    second = container.create_code_quality_analysis_service()

    assert first is second


def test_code_quality_service_is_independent_of_discovery_service():
    container = ApplicationContainer()

    discovery_service = (
        container.create_repository_discovery_integration_service()
    )
    quality_service = container.create_code_quality_analysis_service()

    assert discovery_service is not quality_service


def test_code_quality_service_is_independent_of_source_loading_service():
    container = ApplicationContainer()

    source_service = (
        container.create_repository_source_loading_service()
    )
    quality_service = container.create_code_quality_analysis_service()

    assert source_service is not quality_service


def test_container_preserves_eight_provider_registrations():
    container = ApplicationContainer()

    expected = {
        "ollama",
        "openai",
        "anthropic",
        "gemini",
        "mistral",
        "groq",
        "cohere",
        "deepseek",
    }

    assert set(container.provider_factory.supported_providers()) == expected
