
from appy.application.services.ai_service import AIService
from appy.application.services.provider_factory import ProviderFactory
from appy.application.services.provider_model_service import (
    ProviderModelService,
)
from appy.application.repository_discovery_integration_service import (
    RepositoryDiscoveryIntegrationService,
)
from appy.application.repository_source_loading_service import (
    RepositorySourceLoadingService,
)
from appy.application.code_quality_analysis_service import (
    CodeQualityAnalysisService,
)
from appy.infrastructure.providers import (
    AnthropicProvider,
    CohereProvider,
    DeepSeekProvider,
    GeminiProvider,
    GroqProvider,
    MistralProvider,
    OllamaProvider,
    OpenAIProvider,
)
from appy.infrastructure.providers.registry import (
    InMemoryProviderRegistry,
)


class ApplicationContainer:
    """Central dependency container for application services."""

    def __init__(self) -> None:
        self._provider_registry = InMemoryProviderRegistry()
        self._provider_factory = ProviderFactory()

        self._repository_discovery_service = None
        self._repository_source_loading_service = None
        self._code_quality_analysis_service = None

        self._register_providers()

    def _register_providers(self) -> None:
        """Register all supported AI providers."""

        self._provider_factory.register("ollama", OllamaProvider)
        self._provider_factory.register("openai", OpenAIProvider)
        self._provider_factory.register("anthropic", AnthropicProvider)
        self._provider_factory.register("gemini", GeminiProvider)
        self._provider_factory.register("mistral", MistralProvider)
        self._provider_factory.register("groq", GroqProvider)
        self._provider_factory.register("cohere", CohereProvider)
        self._provider_factory.register("deepseek", DeepSeekProvider)

    @property
    def provider_registry(self) -> InMemoryProviderRegistry:
        return self._provider_registry

    @property
    def provider_factory(self) -> ProviderFactory:
        return self._provider_factory

    def create_provider_model_service(self) -> ProviderModelService:
        return ProviderModelService(
            registry=self._provider_registry,
        )

    def create_ai_service(self, provider_name: str) -> AIService:
        provider = self._provider_factory.create(provider_name)
        return AIService(provider=provider)

    def create_repository_discovery_integration_service(
        self,
    ) -> RepositoryDiscoveryIntegrationService:
        """Return the shared repository discovery service."""

        if self._repository_discovery_service is None:
            self._repository_discovery_service = (
                RepositoryDiscoveryIntegrationService()
            )

        return self._repository_discovery_service

    def create_repository_source_loading_service(
        self,
    ) -> RepositorySourceLoadingService:
        """Return the shared repository source-loading service."""

        if self._repository_source_loading_service is None:
            self._repository_source_loading_service = (
                RepositorySourceLoadingService()
            )

        return self._repository_source_loading_service

    def create_code_quality_analysis_service(
        self,
    ) -> CodeQualityAnalysisService:
        """Return the shared code quality analysis service."""

        if self._code_quality_analysis_service is None:
            self._code_quality_analysis_service = (
                CodeQualityAnalysisService()
            )

        return self._code_quality_analysis_service
